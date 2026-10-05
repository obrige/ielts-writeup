def _extract_title(title_resp, question):
    """从 LLM 响应提取 title 字段, 兼容 JSON dict 或 Python dict repr"""
    import json as _json
    import ast as _ast
    if isinstance(title_resp, dict):
        return (title_resp.get("title") or question[:20])[:120]
    s = str(title_resp or "")
    s = s.strip()
    if s.startswith(chr(123)):
        # 优先 JSON 解析 (双引号)
        try:
            d = _json.loads(s)
            return (d.get("title") or question[:20])[:120]
        except Exception:
            # 退而求其次: Python dict repr (单引号)
            try:
                d = _ast.literal_eval(s)
                return (d.get("title") or question[:20])[:120]
            except Exception:
                return s.strip(chr(0x201c) + chr(0x201d) + chr(0x3002) + chr(0xff01) + chr(0xff1f) + chr(0x3002) + chr(0xff0c) + chr(0x3001) + chr(0xff1b))[:120]
    return s.strip(chr(0x201c) + chr(0x201d) + chr(0x3002) + chr(0xff01) + chr(0xff1f) + chr(0x3002) + chr(0xff0c) + chr(0x3001) + chr(0xff1b))[:120]


def safe_json_loads(s, default=None):
    """Bug: 防御性 json.loads, 损坏数据返回 default"""
    if not s: return default if default is not None else {}
    try: return json.loads(s)
    except (json.JSONDecodeError, TypeError): return default if default is not None else {}


import json, base64, os, re
import asyncio
from sqlalchemy import select
from .database import SessionLocal
from .models import GradingJob
from . import llm, prompts, dimensions as D
from .config import settings

def _split_sentences(essay):
    """\u6309\u4e2d\u82f1\u6587\u6807\u70b9 (\u3002\u3001\uff1f!\uff01?) \u5207\u53e5\u3002\u8fc7\u77ed\u7684\u53e5\u5b50\u4e0d\u53c2\u4e0e\u7cbe\u4fee\u3002"""
    s = essay.strip()
    if not s:
      return []

    parts = re.split(r"(?<=[\u3002!?\uff1f\uff01\.\!\?])\s*", s)
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= 6:  # \u592a\u77ed\u7684\u4e0d\u53c2\u4e0e\u7cbe\u4fee
            out.append(p)
    return out


async def run_job(job_id):
    async with SessionLocal() as db:
        job = (await db.execute(select(GradingJob).where(GradingJob.id == job_id))).scalar_one_or_none()
        if not job:
            return

        # watchdog 已禁用: 用 created_at 判超时会误杀排队久+重试的任务 (Celery 硬时限 3600s + acks_late 已兜底)
        if job.status == "running" and job.created_at:
            pass

        if job.status == "pending":
            job.grading_result = "{}"
        job.status = "running"
        await db.commit()

        text_models = await llm.get_models(db, vision=False)
        vision_models = await llm.get_models(db, vision=True)
        if not text_models:
            job.status = "failed"
            job.error = "无可用文本模型"
            await db.commit()
            raise RuntimeError("无可用文本模型")  # Bug #35补充: 必须 raise 才能让 grade_task 触发退费

        image_b64, mime = await _load_image(job.image_path)

        # 如果有图片且配置了视觉模型，先做一次图片描述
        image_description = None
        vlm_used = False
        used_models = []
        if image_b64 and vision_models:
            try:
                desc_prompt = "请详细描述这张图片的所有内容。如果是流程图，描述所有阶段和步骤；如果是地图，描述所有地点和变化；如果是数据图表，描述所有数据和趋势。用中文回答。"
                image_description, model_name = await llm.call_text_with_fallback(vision_models, desc_prompt, image_b64=image_b64, mime=mime)
                vlm_used = True
                used_models.append(model_name)
            except Exception as e:
                image_description = "[VLM识别失败: " + str(e)[:100] + "]，原图未参与评分"  # Bug #12: 告知用户 VLM 失败
                vlm_used = False

        pre, mname = await llm.call_with_fallback(text_models, prompts.precheck_prompt(job.task_type, job.question, job.essay, image_description=image_description))
        used_models.append(mname)
        job.precheck = pre
        await db.commit()

        if pre.get("is_off_topic") is True or pre.get("safety_ok") is False:  # Bug #9: 严格布尔比较，避免 "false" 字符串 truthy
            job.status = "flagged"
            await db.commit()
            return

        sub_all = {}
        # Retry 防御
        existing_dims = (safe_json_loads(job.grading_result) if job.grading_result else {}).get("dimensions", {}) if job.grading_result else {}
        for dc in D.DIM_ORDER[job.task_type]:
            sub_all[dc] = []
            if existing_dims.get(dc):
                for s in existing_dims[dc].get("sub_scores", []):
                    if s.get("score") is not None:
                        sub_all[dc].append(s)

        # 并发评分 sub-dim (信号量限制)
        _sem = asyncio.Semaphore(getattr(settings, "GRADER_CONCURRENCY", 4))
        _commit_lock = asyncio.Lock()

        async def _score_sub(dc, area):
            async with _sem:
                try:
                    r, mname = await llm.call_with_fallback(text_models,
                            prompts.sub_dimension_prompt(job.task_type, dc, area, job.question, job.essay, image_description=image_description))
                    used_models.append(mname)
                except Exception as e:
                    r = {"area": area, "score": None, "error": str(e)}
                sub_all[dc].append(r)
                async with _commit_lock:
                    job.grading_result = json.dumps({"dimensions": {k: {"sub_scores": v} for k, v in sub_all.items() if v}, "has_image": image_b64 is not None, "vlm_used": vlm_used})
                    await db.commit()

        # 断点续评: 已出分的子维度跳过, 只补缺的 (之前 done_areas 未定义是 NameError, 正确修法是定义它而非删过滤)
        done_areas = {dc: {s.get("area") for s in sub_all.get(dc, []) if s.get("score") is not None} for dc in D.DIM_ORDER[job.task_type]}
        _tasks = [_score_sub(dc, area) for dc in D.DIM_ORDER[job.task_type] for area in D.DIMENSIONS[job.task_type][dc]["subs"] if area not in done_areas[dc]]
        if _tasks:
            await asyncio.gather(*_tasks)
        # Bug Fix: 重试所有 score=None 的 sub-scores (每个 dim 必须所有 sub-scores 完成才合成)
        _retry_tasks = []
        for dc in D.DIM_ORDER[job.task_type]:
            for area in D.DIMENSIONS[job.task_type][dc]["subs"]:
                done = [s for s in sub_all.get(dc, []) if s.get("area") == area and s.get("score") is not None]
                if not done:
                    _retry_tasks.append(_score_sub(dc, area))
        if _retry_tasks:
            await asyncio.gather(*_retry_tasks)
        # dim-synth 初始化：dims 以 sub_all + 已合成结果为基础
        dims = {dc: {"sub_scores": list(sub_all.get(dc, []))} for dc in D.DIM_ORDER[job.task_type]}
        for dc in D.DIM_ORDER[job.task_type]:
            if existing_dims.get(dc) and existing_dims[dc].get("score") is not None:
                # Retry 防御：保留之前已综合的维度结果
                dims[dc].update(existing_dims[dc])

        async def _synth(dc):
            async with _sem:
                try:
                    d, mname = await llm.call_with_fallback(text_models,
                            prompts.dimension_synthesis_prompt(job.task_type, dc, job.question, job.essay, sub_all[dc], image_description=image_description))
                    used_models.append(mname)
                    d["sub_scores"] = sub_all[dc]
                except Exception as e:
                    d = {"dimension_code": dc, "score": None, "error": str(e), "sub_scores": sub_all[dc]}
                # Bug Fix: 如果 LLM 合成失败或没返回 score, 重试一次, 仍失败用 sub_scores 平均值
                if not isinstance(d.get("score"), (int, float)):
                    try:
                        d2, mname2 = await llm.call_with_fallback(text_models,
                                prompts.dimension_synthesis_prompt(job.task_type, dc, job.question, job.essay, sub_all[dc], image_description=image_description))
                        used_models.append(mname2)
                        if isinstance(d2.get("score"), (int, float)):
                            d = d2
                            d["sub_scores"] = sub_all[dc]
                    except Exception:
                        pass
                if not isinstance(d.get("score"), (int, float)):
                    sub_scores = [s.get("score") for s in sub_all[dc] if isinstance(s.get("score"), (int, float))]
                    if sub_scores:
                        avg = D.ielts_round(sum(sub_scores) / len(sub_scores))
                        d["score"] = avg
                        d.setdefault("analysis_summary", f"[综合分数] 该维度基于 {len(sub_scores)} 个子维度评分加权综合（LLM 合成调用失败时的回退方案）")
                dims[dc].update(d)
                async with _commit_lock:
                    job.grading_result = json.dumps({"dimensions": dims, "has_image": image_b64 is not None, "vlm_used": vlm_used})
                    await db.commit()

        # Bug Fix: 每个 dim 必须所有 sub-scores 完成才合成, 否则用 sub_scores 平均值
        _synth_tasks = []
        for dc in D.DIM_ORDER[job.task_type]:
            if dims[dc].get("score") is not None:
                continue
            completed_areas = {s.get("area") for s in sub_all.get(dc, []) if s.get("score") is not None}
            expected_areas = set(D.DIMENSIONS[job.task_type][dc]["subs"])
            if completed_areas == expected_areas:
                _synth_tasks.append(_synth(dc))
            else:
                sub_scores = [s.get("score") for s in sub_all.get(dc, []) if isinstance(s.get("score"), (int, float))]
                if sub_scores:
                    avg = D.ielts_round(sum(sub_scores) / len(sub_scores))
                    dims[dc].update({"score": avg, "sub_scores": list(sub_all.get(dc, [])),
                                    "analysis_summary": "[综合分数] 该维度仅基于 " + str(len(sub_scores)) + "/" + str(len(expected_areas)) + " 个子维度评分（部分子维度评分失败时的回退方案）"})
        if _synth_tasks:
            # Bug #29
            await asyncio.gather(*_synth_tasks, return_exceptions=True)

        scores = [d["score"] for d in dims.values() if isinstance(d.get("score"), (int, float))]
        predicted = D.ielts_round(sum(scores) / len(scores)) if scores else None

        try:
            sugg, mname = await llm.call_with_fallback(text_models, prompts.suggestion_prompt(job.task_type, job.question, job.essay, image_description=image_description))
            used_models.append(mname)
        except Exception as e:
            sugg = {"error": str(e)}

        # Retry 防御：从已有 result 拉回已评的句子，避免重 LLM 浪费 token
        existing_sents = (safe_json_loads(job.grading_result) if job.grading_result else {}).get("sentence_suggestions", []) or []
        sentence_suggestions = list(existing_sents)
        sentences = _split_sentences(job.essay)
        if sentences:
            # 过滤掉 score=None 的 dim/sentence，避免给 LLM 噪声
            sub_dict = {dc: [s for s in (sub_all.get(dc) or []) if s.get("score") is not None] for dc in D.DIM_ORDER[job.task_type]}
            dim_dict = {dc: {"score": (dims.get(dc) or {}).get("score"), "analysis_summary": (dims.get(dc) or {}).get("analysis_summary")} for dc in D.DIM_ORDER[job.task_type] if (dims.get(dc) or {}).get("score") is not None}

            async def _score_sentence(i, sent):
                async with _sem:
                    if i < len(sentence_suggestions) and sentence_suggestions[i]:
                        return  # 已有，跳过
                    # 上下文截断 300 字符，避免 prompt 过长
                    before = " ".join(sentences[:i])[-300:]
                    after = " ".join(sentences[i+1:])[:300]
                    try:
                        r, mname = await llm.call_with_fallback(text_models,
                                prompts.sentence_suggestion_prompt(job.task_type, i, sent, before, after, sub_dict, dim_dict, len(sentences), image_description))
                        used_models.append(mname)
                    except Exception as e:
                        r = {"needs_revision": False, "error": str(e)}
                    async with _commit_lock:
                        while len(sentence_suggestions) <= i:
                            sentence_suggestions.append(None)

                        sentence_suggestions[i] = {**r, "_index": i} if isinstance(r, dict) else r

                        job.grading_result = json.dumps({**safe_json_loads(job.grading_result), "sentence_suggestions": list(sentence_suggestions)})
                        await db.commit()

            # 只对未评的句子启动 LLM
            pending = [(i, s) for i, s in enumerate(sentences) if i >= len(sentence_suggestions) or not sentence_suggestions[i]]
            if pending:
                # Bug #29
                await asyncio.gather(*[_score_sentence(i, s) for i, s in pending], return_exceptions=True)

        try:
            title_resp, _ = await llm.call_with_fallback(text_models, prompts.title_prompt(job.task_type, job.question, job.essay))
            job.title = _extract_title(title_resp, job.question)
        except Exception:
            job.title = (job.question[:20] + "\u2026") if len(job.question) > 20 else job.question

        _img_desc_truncated = (image_description or "")[:1500] if image_description else None
        # 保留 label/is_vision
        from .models import ModelConfig as _MC
        _model_rows = {}
        if used_models:
            try:
                _rs = await db.execute(_MC.__table__.select().where(_MC.name.in_(list(set(used_models)))))
                _model_rows = {r.name: {"label": r.label or r.name, "is_vision": bool(r.is_vision)} for r in _rs}
            except Exception:
                pass
        unique_models = [
            {"name": n, "label": _model_rows.get(n, {}).get("label", n), "is_vision": _model_rows.get(n, {}).get("is_vision", False)}
            for n in dict.fromkeys(used_models)
        ]

        final_sents = []
        for _i, _s in enumerate(sentence_suggestions):
            if _s is None: continue
            if isinstance(_s, dict) and "_index" not in _s:
                _s["_index"] = _i
            final_sents.append(_s)
        job.grading_result = json.dumps({"dimensions": dims, "predicted_band": predicted, "suggestion": sugg,
                       "has_image": image_b64 is not None, "vlm_used": vlm_used,
                       "image_description": _img_desc_truncated,  # Bug #15
                       "sentence_suggestions": final_sents,  # Bug: 最终保存漏掉了这个字段
                       "models_used": unique_models})
        # 任务快结束前, 检查是否被用户取消. 只刷 status 字段, 避免覆盖刚构建的 grading_result
        await db.refresh(job, attribute_names=["status"])
        if job.status == "cancelled":
            return
        job.status = "done"
        from datetime import datetime, timezone
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()


async def _load_image(path):
    if not path or not os.path.exists(path):
        return None, None
    import mimetypes
    with open(path, "rb") as _f:
        data = _f.read()
    mime = mimetypes.guess_type(path)[0] or "image/octet-stream"  # Bug #26: 用 mimetypes 推断，关闭文件句柄
    try:
        from io import BytesIO
        from PIL import Image
        img = Image.open(BytesIO(data))
        w, h = img.size
        if w < 64 or h < 64:
            new_w = max(w, 64)
            new_h = max(h, 64)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="PNG")
            data = buf.getvalue()
            mime = "image/png"
    except Exception:
        pass
    return base64.b64encode(data).decode(), mime
