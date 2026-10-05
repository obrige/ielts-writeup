import json
from .dimensions import DIMENSIONS

SYSTEM = (
    "\u4f60\u662f\u7ecf\u8fc7\u8ba4\u8bc1\u7684\u96c5\u601d\u5199\u4f5c\u8003\u5b98\uff0c\u53ea\u8bc4\u6307\u5b9a\u7684\u4e00\u4e2a\u7ef4\u5ea6/\u5b50\u7ef4\u5ea6\uff0c\u53ea\u8f93\u51fa\u5408\u6cd5 JSON\uff0c"
    "\u4e0d\u8f93\u51fa markdown\uff0c\u4e0d\u8f93\u51fa\u601d\u8003\u8fc7\u7a0b\uff0c\u4e25\u683c\u4f9d\u636e\u5b98\u65b9 Band Descriptors\u3002"
)
CN = (
    "\u6240\u6709\u6587\u5b57\u5185\u5bb9\uff08analysis_summary\u3001explanation\u3001current_do\u3001to_reach_next\u3001"
    "strength\u3001issue\u3001suggestion\u3001impact \u7b49\uff09\u4e00\u5f8b\u7528\u4e2d\u6587\u8f93\u51fa\u3002"
)
USER_WRAPPER = "user_content"
WRAP = lambda t: "<" + USER_WRAPPER + ">\n" + t + "\n</" + USER_WRAPPER + ">"


# \u5b98\u65b9 IELTS Band Descriptors (Task 1 + Task 2)
BAND = {
"task1": {
"TA": {
9:"All the requirements of the task are fully and appropriately satisfied. There may be extremely rare lapses in content.",
8:"The response covers all the requirements of the task appropriately, relevantly and sufficiently.",
7:"The response covers the requirements of the task. The content is relevant and accurate \u2013 there may be a few omissions or lapses.",
6:"The response focuses on the requirements of the task and an appropriate format is used.",
5:"The response generally addresses the requirements of the task. The format may be inappropriate in places.",
4:"The response is an attempt to address the task. Few key features have been selected.",
3:"The response does not address the requirements of the task.",
2:"The content barely relates to the task.",
1:"Responses of 20 words or fewer are rated at Band 1.",
0:"Should only be used where a candidate did not attend or attempt the question in any way.",
},
"CC": {
9:"The message can be followed effortlessly. Cohesion is used in such a way that it very rarely attracts attention.",
8:"The message can be followed with ease. Information and ideas are logically sequenced.",
7:"Information and ideas are logically organised and there is a clear progression throughout the response.",
6:"Information and ideas are generally arranged coherently and there is a clear overall progression.",
5:"Organisation is evident but is not wholly logical and there may be a lack of overall progression.",
4:"Information and ideas are evident but not arranged coherently, and there is no clear progression.",
3:"There is no apparent logical organisation.",
2:"There is little evidence of control of organisational features.",
1:"Responses of 20 words or fewer are rated at Band 1.",
0:"Should only be used where a candidate did not attend or attempt the question in any way.",
},
"LR": {
9:"Full flexibility and precise use are evident within the scope of the task.",
8:"A wide resource is fluently and flexibly used to convey precise meanings within the scope of the task.",
7:"The resource is sufficient to allow some flexibility and precision.",
6:"The resource is generally adequate and appropriate for the task.",
5:"The resource is limited but minimally adequate for the task.",
4:"The resource is inadequate for the task.",
3:"Vocabulary is inadequate for the task.",
2:"Very limited resource: very few words or chunks of language.",
1:"Responses of 20 words or fewer are rated at Band 1.",
0:"Should only be used where a candidate did not attend or attempt the question in any way.",
},
"GRA": {
9:"A wide range of structures is used with full flexibility and control. Punctuation and grammar are used appropriately throughout.",
8:"A wide range of structures is used flexibly. The majority of sentences are error-free.",
7:"A variety of complex structures is used with some flexibility and accuracy.",
6:"A mix of simple and complex sentence forms is used but errors may be present.",
5:"The range of structures is limited and is used repetitively.",
4:"A limited range of structures is used.",
3:"Sentence forms are attempted but errors in grammar and punctuation predominate.",
2:"There is little evidence of control in sentence formation.",
1:"Responses of 20 words or fewer are rated at Band 1.",
0:"Should only be used where a candidate did not attend or attempt the question in any way.",
},
},
"task2": {
"TR": {
9:"The prompt is fully addressed. A fully developed position is presented in the response with relevant, extended and well supported ideas.",
8:"The prompt is well addressed. A clear and well-developed position is presented in the response.",
7:"The prompt is addressed. A clear position is presented in the response with relevant main body paragraphs.",
6:"The prompt is mainly addressed. A position is presented although it may not be wholly clear.",
5:"The prompt is only partly addressed. A position is present but is unclear.",
4:"The prompt is only minimally addressed. The answer is largely irrelevant.",
3:"No relevant part of the prompt is addressed.",
2:"The answer barely relates to the prompt.",
1:"Responses of 20 words or fewer are rated at Band 1.",
0:"Should only be used where a candidate did not attend or attempt the question in any way.",
},
"CC": {
9:"The message can be followed effortlessly. Cohesion is used in such a way that it very rarely attracts attention.",
8:"The message can be followed with ease. Information and ideas are logically sequenced.",
7:"Information and ideas are logically organised and there is a clear progression throughout the response.",
6:"Information and ideas are generally arranged coherently and there is a clear overall progression.",
5:"Organisation is evident but is not wholly logical and there may be a lack of overall progression.",
4:"Information and ideas are evident but not arranged coherently, and there is no clear progression.",
3:"There is no apparent logical organisation.",
2:"There is little evidence of control of organisational features.",
1:"Responses of 20 words or fewer are rated at Band 1.",
0:"Should only be used where a candidate did not attend or attempt the question in any way.",
},
"LR": {
9:"Full flexibility and precise use are evident within the scope of the task.",
8:"A wide resource is fluently and flexibly used to convey precise meanings within the scope of the task.",
7:"The resource is sufficient to allow some flexibility and precision.",
6:"The resource is generally adequate and appropriate for the task.",
5:"The resource is limited but minimally adequate for the task.",
4:"The resource is inadequate for the task.",
3:"Vocabulary is inadequate for the task.",
2:"Very limited resource: very few words or chunks of language.",
1:"Responses of 20 words or fewer are rated at Band 1.",
0:"Should only be used where a candidate did not attend or attempt the question in any way.",
},
"GRA": {
9:"A wide range of structures is used with full flexibility and control. Punctuation and grammar are used appropriately throughout.",
8:"A wide range of structures is used flexibly. The majority of sentences are error-free.",
7:"A variety of complex structures is used with some flexibility and accuracy.",
6:"A mix of simple and complex sentence forms is used but errors may be present.",
5:"The range of structures is limited and is used repetitively.",
4:"A limited range of structures is used.",
3:"Sentence forms are attempted but errors in grammar and punctuation predominate.",
2:"There is little evidence of control in sentence formation.",
1:"Responses of 20 words or fewer are rated at Band 1.",
0:"Should only be used where a candidate did not attend or attempt the question in any way.",
},
},
}


def _band_text(task_type, dc):
    return "\n".join("Band " + str(b) + ": " + t for b in sorted(BAND[task_type][dc], reverse=True) for t in [BAND[task_type][dc][b]])


def precheck_prompt(task_type, question, essay, image_description=None):
    min_words = 250 if task_type == "task2" else 150
    img_ctx = ("\n\n## 题目图表描述 (VLM识别)\n" + WRAP(image_description) if image_description else "")
    q = WRAP(question); e = WRAP(essay)
    return (SYSTEM +
            "\n## 任务类型\n" + ("Task 2 (大作文, 最少 " + str(min_words) + " 词)" if task_type == "task2" else "Task 1 (小作文, 最少 " + str(min_words) + " 词)") +
            "\n\n## 题目\n" + q + img_ctx +
            "\n\n## 学生作文\n" + e +
            "\n\n## 你的任务: 对作文进行**严格预检**\n" +
            "1. **字数统计**: 用空格分词, 给出实际 word_count (整数)\\n" +
            "2. **字数下限**: 若 word_count < " + str(min_words) + " 则 below_min_words=true, 并在 word_count_shortfall 字段给出差额\\n" +
            "3. **离题判断**: 作文是否回应题目? 给出 is_off_topic (bool) 和 relevance (relevant/partial/off) 和 relevance_reason (1-2 句解释)\\n" +
            "4. **格式检查**: format_ok (是否规范的小作文/大作文, 无 bullet list), uses_bullet_points (bool)\\n" +
            "5. **抄袭判断**: looks_memorised_or_copied (bool)\\n" +
            "6. **安全检查**: safety_ok (bool, 是否含违规内容)\\n\n" +
            CN +
            "\n\n## 输出严格 JSON (无 markdown)\n" +
            "{\"word_count\": <整数>, \"word_count_shortfall\": <整数, 0 表示达标>, \"below_min_words\": <bool>, \"is_off_topic\": <bool>, \"relevance\": \"<relevant|partial|off>\", \"relevance_reason\": \"<一句话解释>\", \"format_ok\": <bool>, \"uses_bullet_points\": <bool>, \"looks_memorised_or_copied\": <bool>, \"safety_ok\": <bool>}"
    )


def sub_dimension_prompt(task_type, dc, area, question, essay, with_image=False, image_description=None):
    q = WRAP(question); e = WRAP(essay)
    img = ("\n\n## \u9898\u76ee\u56fe\u8868\u63cf\u8ff0 (VLM\u8bc6\u522b)\n" + image_description if image_description else ("\n\n## \u4f5c\u6587\u542b\u56fe\u7247, \u8bf7\u7ed3\u5408\u56fe\u7247\u7406\u89e3\n" if with_image else ""))
    min_words = 250 if task_type == "task2" else 150
    word_count = len((essay or "").split())
    word_warning = ("\n\n**\u5b57\u6570\u8b66\u544a**: \u672c\u7bc7\u6587\u7ae0 " + str(word_count) + " \u8bcd,\u5c11\u4e8e\u9898\u76ee\u8981\u6c42\u7684 " + str(min_words) + " \u8bcd,\u8bc4\u5206\u65f6\u8981\u8003\u8651\u5b57\u6570\u4e0d\u8db3\u7684\u5f71\u54cd." if word_count < min_words else "")
    return (SYSTEM +
            "\n\n## \u4efb\u52a1\u7c7b\u578b\n" + ("Task 2 (\u5927\u4f5c\u6587, \u6700\u5c11 " + str(min_words) + " \u8bcd)" if task_type == "task2" else "Task 1 (\u5c0f\u4f5c\u6587, \u6700\u5c11 " + str(min_words) + " \u8bcd)") +
            "\n\n## \u5b66\u751f\u4f5c\u6587 (" + str(word_count) + " \u8bcd)\n" + e +
            "\n\n## \u9898\u76ee\n" + q + img +
            word_warning +
            "\n\n## \u4f60\u7684\u4efb\u52a1: \u53ea\u8bc4 **" + DIMENSIONS[task_type][dc]["name"] + " \u2192 " + area + "** \u8fd9\u4e00\u9879, \u4e25\u683c\u6309 0-9 \u5206\u6253\u5206 (\u53ef\u542b .5).\n" +
            "\u8bf7\u4f9d\u636e Band Descriptors \u548c\u5b9e\u9645\u5185\u5bb9\u8d28\u91cf\u8bc4\u5206, \u81ea\u884c\u5224\u65ad. \u5b57\u6570\u4e0d\u8db3\u5e94\u5728 explanation \u4e2d\u660e\u786e\u6307\u51fa (\u5f15\u7528\u539f\u6587\u8bf4\u660e\u8bba\u70b9\u662f\u5426\u5b9e\u9645\u5c55\u5f00).\n" +
            "### \u5b98\u65b9 Band Descriptors (0-9 \u5206\u5b8c\u6574\u53c2\u8003, \u6309\u4ece\u9ad8\u5230\u4f4e\u6392\u5e8f)\n" + _band_text(task_type, dc) + "\n\n" +
            "### \u8bc4\u5206\u8981\u70b9 (\u9488\u5bf9 " + area + "):\n" +
            _sub_area_guidance(task_type, dc, area) + "\n\n" +
            CN +
            "\n\n### \u4e25\u683c\u8f93\u51fa JSON (\u65e0 markdown, \u5b57\u6bb5\u987a\u5e8f\u56fa\u5b9a)\n" +
            "{\"area\":\"" + area + "\",\"score\":<0-9 \u542b .5>,\"explanation\":\"<2-3 \u53e5\u7ed9\u5206\u7406\u7531, \u5f15\u7528\u539f\u6587\u5173\u952e\u77ed\u8bed>\",\"current_do\":\"<1 \u53e5\u5f53\u524d\u8868\u73b0>\",\"to_reach_next\":\"<1-2 \u53e5\u5177\u4f53\u63d0\u5347\u8def\u5f84, \u7ed9\u51fa\u4e0b\u4e00\u6863\u7684\u5177\u4f53\u52a8\u4f5c>\"}"
    )

def _sub_area_guidance(task_type, dc, area):
    """针对每个子维度的具体评分指引"""
    g = {
        ("task2", "TR", "回应题目"): "判断作文是否直接回应题目所有部分. 若题目包含 agree/disagree, 立场必须明确; 若包含 discuss both, 必须两边都涉及.",
        ("task2", "TR", "立场明确"): "评估立场表达是否清晰一致, 全文立场是否统一.",
        ("task2", "TR", "观点拓展"): "每个观点是否充分扩展 (举例/解释/对比), 还是仅停留在断言.",
        ("task2", "TR", "内容疏漏"): "是否有未回应的题目要点, 内容是否完整覆盖.",
        ("task2", "CC", "组织与逻辑"): "整体是否有清晰逻辑结构, 主体段是否各承担一个论点.",
        ("task2", "CC", "段落结构"): "是否合理分段 (建议 4-5 段: 引言+2-3 主体段+结论). 单段大杂烩扣分.",
        ("task2", "CC", "逻辑推进"): "段落内和段落间是否有递进逻辑, 而非简单堆叠.",
        ("task2", "CC", "指代与替换"): "it/this/these 等指代是否清晰, 是否有同义替换避免重复.",
        ("task2", "CC", "逻辑衔接"): "连接词是否多样 (however/therefore/in contrast 等), 是否过度依赖简单 However.",
        ("task2", "LR", "词汇广度"): "用词是否多样, 是否有 less common vocabulary (如 acquire, detrimental, mitigate).",
        ("task2", "LR", "用词精准"): "用词是否精确 (如: enhance vs improve, detrimental vs bad).",
        ("task2", "LR", "词汇搭配"): "词伙是否自然 (如: pose a threat, draw a conclusion, tackle the issue).",
        ("task2", "LR", "拼写与构词"): "拼写和构词完全正确得高分; 字数极短时此分高意义不大.",
        ("task2", "GRA", "句式丰富度"): "是否使用复杂句 (定语从句/状语从句/名词性从句). 全部简单句 = 最高 5 分.",
        ("task2", "GRA", "语法准确性"): "主谓一致/时态/冠词/介词是否准确.",
        ("task2", "GRA", "语法及标点错误"): "有无明显语法错误, 标点使用是否正确.",
    }
    return g.get((task_type, dc, area), "依据官方 Band Descriptors 评分.")


def dimension_synthesis_prompt(task_type, dc, question, essay, sub_results, image_description=None):
    q = WRAP(question); e = WRAP(essay)
    img_ctx = ("\n\n## \u9898\u76ee\u56fe\u8868\u63cf\u8ff0 (VLM\u8bc6\u522b)\n" + WRAP(image_description) if image_description else "")
    min_words = 250 if task_type == "task2" else 150
    word_count = len((essay or "").split())
    word_warning = ("\n\n**\u5b57\u6570\u8b66\u544a**: \u672c\u7bc7\u6587\u7ae0 " + str(word_count) + " \u8bcd,\u5c11\u4e8e\u9898\u76ee\u8981\u6c42\u7684 " + str(min_words) + " \u8bcd,\u7efc\u5408\u8bc4\u5206\u65f6\u8981\u8003\u8651\u5b57\u6570\u4e0d\u8db3\u7684\u5f71\u54cd." if word_count < min_words else "")
    sub_summary = []
    for sr in sub_results:
        if sr and isinstance(sr, dict):
            sub_summary.append("- " + sr.get("area", "") + ": " + str(sr.get("score", "?")) + " \u5206 \u2014 " + (sr.get("explanation", "") or "")[:150])
    sub_block = "\n".join(sub_summary)
    return (SYSTEM +
            "\n\n## \u4efb\u52a1\u7c7b\u578b\n" + ("Task 2 (\u5927\u4f5c\u6587, \u6700\u5c11 " + str(min_words) + " \u8bcd)" if task_type == "task2" else "Task 1 (\u5c0f\u4f5c\u6587, \u6700\u5c11 " + str(min_words) + " \u8bcd)") +
            "\n\n## \u9898\u76ee\n" + q + img_ctx +
            "\n\n## \u5b66\u751f\u4f5c\u6587 (" + str(word_count) + " \u8bcd)\n" + e +
            "\n\n## \u5b50\u7ef4\u5ea6\u8bc4\u5206 (\u4f9b\u53c2\u8003)\n" + sub_block +
            word_warning +
            "\n\n## \u4f60\u7684\u4efb\u52a1: \u7efc\u5408\u8bc4\u4f30 **" + DIMENSIONS[task_type][dc]["name"] + "** \u8fd9\u4e00\u5927\u7ef4\u5ea6, \u7ed9\u51fa 0-9 \u5206 (\u542b .5).\n" +
            "### \u8bc4\u5206\u6b65\u9aa4 (\u52a1\u5fc5\u6309\u6b64\u63a8\u7406):\n" +
            "1. **\u9010\u5b57\u68c0\u67e5**: \u901a\u8bfb\u4f5c\u6587, \u6807\u51fa 3-5 \u4e2a\u539f\u6587\u5173\u952e\u77ed\u8bed (\u5e26\u53cc\u5f15\u53f7) \u7528\u4e8e\u652f\u6491\u4f60\u7684\u5224\u65ad\n" +
            "2. **\u5bf9\u7167 Band Descriptor**: \u627e\u51fa\u6700\u5951\u5408\u7684\u6863\u4f4d\n" +
            "3. **\u68c0\u67e5\u8d1f\u9762\u7279\u5f81**: \u662f\u5426\u6709 Band 6+ \u5fc5\u5907\u7684\u8fde\u8d2f\u6027\u3001\u5177\u4f53\u4f8b\u8bc1\u3001\u590d\u6742\u7ed3\u6784\n" +
            "4. **\u7ed9\u51fa\u6700\u7ec8\u5206**: \u4e25\u683c\u6309 0-9 \u5206 (\u53ef\u542b .5). \u7efc\u5408\u5185\u5bb9\u8d28\u91cf\u4e0e\u5b57\u6570\u81ea\u884c\u5224\u65ad. \u5b57\u6570\u4e0d\u8db3\u5e94\u5728 analysis_summary \u4e2d\u660e\u786e\u6307\u51fa.\n" +
            "### \u5b98\u65b9 Band Descriptors\n" + _band_text(task_type, dc) + "\n\n" +
            CN +
            "\n\n### \u4e25\u683c\u8f93\u51fa JSON\n" +
            "{\"dimension_code\":\"" + dc + "\",\"score\":<0-9 \u542b .5>,\"analysis_summary\":\"<2-3 \u53e5, \u5f15\u7528\u539f\u6587>\",\"strengths\":[\"<\u4f18\u52bf 1>\",\"<\u4f18\u52bf 2>\"],\"improvements\":[\"<\u5f85\u6539\u8fdb 1>\",\"<\u5f85\u6539\u8fdb 2>\"]}"
    )

def suggestion_prompt(task_type, question, essay, image_description=None):
    img_ctx = ("\n\n## \u9898\u76ee\u56fe\u8868\u63cf\u8ff0 (VLM\u8bc6\u522b)\n" + WRAP(image_description) if image_description else "")
    min_words = 250 if task_type == "task2" else 150
    word_count = len((essay or "").split())
    word_warning = ("\n\n**\u5b57\u6570\u8b66\u544a**: \u672c\u7bc7\u6587\u7ae0 " + str(word_count) + " \u8bcd,\u5c11\u4e8e\u9898\u76ee\u8981\u6c42\u7684 " + str(min_words) + " \u8bcd,\u7efc\u5408\u5efa\u8bae\u65f6\u8981\u8003\u8651\u5b57\u6570\u4e0d\u8db3\u7684\u5f71\u54cd." if word_count < min_words else "")
    q = WRAP(question); e = WRAP(essay)
    return (SYSTEM +
            "\n\n## \u4efb\u52a1\u7c7b\u578b\n" + ("Task 2 (\u5927\u4f5c\u6587, \u6700\u5c11 " + str(min_words) + " \u8bcd)" if task_type == "task2" else "Task 1 (\u5c0f\u4f5c\u6587, \u6700\u5c11 " + str(min_words) + " \u8bcd)") +
            "\n\n## \u9898\u76ee\n" + q + img_ctx +
            "\n\n## \u5b66\u751f\u4f5c\u6587 (" + str(word_count) + " \u8bcd)\n" + e +
            word_warning +
            "1. **\u6574\u4f53\u53cd\u9988** (overall_feedback): 3-5 \u53e5, \u6982\u62ec\u4e3b\u8981\u95ee\u9898, \u5fc5\u987b\u6307\u51fa**\u5b57\u6570\u662f\u5426\u8fbe\u6807, \u5b9e\u9645\u5b8c\u6210\u5ea6** (\u5305\u62ec\u5b57\u6570\u3001\u56de\u5e94\u5b8c\u6574\u5ea6). \u7efc\u5408\u8bc4\u4f30.\n" +
            "2. **\u6bb5\u843d\u5efa\u8bae** (paragraphs): \u6570\u7ec4, \u6bcf\u6bb5\u7ed9\u4e00\u4e2a\u5bf9\u8c61 {paragraph: <\u6bb5\u53f7>, items: [{error_type, issue, suggestion, before, after}]}. \u6bb5\u843d\u53f7 1-based. \u82e5\u4f5c\u6587\u53ea\u6709 1 \u6bb5, \u4e5f\u6309 1 \u6bb5\u8f93\u51fa.\n" +
            CN +
            "\n\n### \u4e25\u683c\u8f93\u51fa JSON\n" +
            "{\"overall_feedback\":\"<3-5 \u53e5\u603b\u7ed3>\",\"paragraphs\":[{\"paragraph\":<\u6bb5\u53f7>,\"items\":[{\"error_type\":\"<\u7528\u8bcd/\u8bed\u6cd5/\u903b\u8f91/\u7ed3\u6784>\",\"issue\":\"<\u95ee\u9898>\",\"suggestion\":\"<\u5982\u4f55\u6539>\",\"before\":\"<\u539f\u53e5>\",\"after\":\"<\u6539\u540e>\"}]}]}"
    )

def title_prompt(task_type, question, essay):
    q = WRAP(question); e = WRAP(essay)
    return ("你是一位辅导老师.\n\n" + SYSTEM +
            "\n\n## 题目\n" + q +
            "\n\n## 作文\n" + e +
            "\n\n## 你的任务: 用 8-15 字中文概括作文主题\n" + CN +
            "\n\n### 输出严格 JSON\n" +
            "{\"title\":\"<8-15 字中文标题>\"}"
    )


def sentence_suggestion_prompt(task_type, sentence_idx, sentence, essay_before, essay_after, sub_results_dict, dim_results_dict, total_sentences, image_description=None):
    """逐句精修 prompt. 带入全部 16 子维度 + 4 大维度评分作为上下文."""
    sub_summary = []
    for dc, subs in sub_results_dict.items():
        sub_summary.append("\n## " + dc + " 子维度评分")
        for s in subs:
            if s and isinstance(s, dict):
                sub_summary.append("- " + s.get("area", "") + ": " + str(s.get("score", "?")) + " 分 | " + (s.get("explanation", "") or "")[:100])
    sub_block = "\n".join(sub_summary)

    dim_summary = []
    for dc, d in dim_results_dict.items():
        if not d:
            continue
        dim_summary.append("\n## " + dc + ": " + str(d.get("score", "?")) + " 分")
        if d.get("analysis_summary"):
            dim_summary.append("  " + d["analysis_summary"])
    dim_block = "\n".join(dim_summary)

    return ("你是一位严谨的雅思写作精修老师。仅对给定的 1 句进行诊断与修订, 出句必须与原句不同。\n\n"
        + SYSTEM
        + "\n\n## 题目\n" + ("task1" if task_type == "task1" else "task2")
        + "\n\n## 该句位置\n全文第 " + str(sentence_idx + 1) + " / " + str(total_sentences) + " 句\n\n## 原句 (待修订)\n" + sentence
        + "\n\n## 上下文\n[上文]\n" + (essay_before[-200:] if essay_before else "(start)")
        + "\n[本句]\n>> " + sentence + "\n[下文]\n" + (essay_after[:200] if essay_after else "(end)")
        + (("\n\n## 题目图表描述\n" + image_description) if image_description else "")
        + "\n\n## 4 大维度评分" + dim_block
        + "\n\n## 16 子维度评分" + sub_block
        + "\n\n## 你的任务\n"
        + "1. 诊断原句: 有语法 / 搭配 / 用词 / 连贯性 / 准确性 / 表达中的 1-3 个问题, 如果都不难可以 needs_revision=false\n"
        + "2. 给出 revised: 修订后的完整句子, 与原句不同\n"
        + "3. 定位 error_type: 语法错误/搭配不当/用词不准/连贯不顺/表达生硬/词汇简陋\n"
        + "4. 额外给出 analysis: 1-2 句说明为什么\n\n"
        + CN
        + "\n输出 JSON 示例:\n{\"needs_revision\": true, \"original\": \"He go to school yesterday.\", \"revised\": \"He went to school yesterday.\", \"error_type\": \"语法错误\", \"analysis\": \"一般过去时应用 went 而不是 go\"}\n\n如果该句表达准确、没有语法或表达问题，请返回 needs_revision=false。\nrevised 字段在 needs_revision=false 时可以是原句原文。"
    )


def sample_essay_prompt(task_type, question, original_essay, dimensions_data, sentence_suggestions=None, image_description=None):
    q = WRAP(question)
    e = WRAP(original_essay)
    img_ctx = ("\n## Image Description (VLM-recognised chart/diagram)\n" + WRAP(image_description)) if image_description else ""
    issues_summary = []
    if dimensions_data:
        for dc, d in dimensions_data.items():
            score = d.get("score", "?")
            analysis = (d.get("analysis_summary", "") or "")[:300]
            issues_summary.append("- " + str(dc) + ": " + str(score) + " - " + analysis)
    issues_block = chr(10).join(issues_summary) if issues_summary else "(none)"
    sent_summary = []
    if sentence_suggestions:
        rev_sents = [s for s in sentence_suggestions if s and s.get("needs_revision") and s.get("original") and s.get("revised")]
        for s in rev_sents[:8]:
            sent_summary.append("- ORIG: " + s["original"][:200] + "  ->  REVISED: " + s["revised"][:200])
    sent_block = chr(10).join(sent_summary) if sent_summary else "(none)"
    target_words = "250-300" if task_type == "task2" else "150-200"
    avg_score = None
    if dimensions_data:
        valid_scores = [d.get("score") for d in dimensions_data.values() if isinstance(d.get("score"), (int, float))]
        if valid_scores:
            avg_score = sum(valid_scores) / len(valid_scores)
    if avg_score is None:
        target_band = "Band 7-7.5"
        target_score = 7.0
    else:
        target_score = round(avg_score + 0.5, 1)
        target_score = round(target_score * 2) / 2
        if target_score > 9.0:
            target_score = 9.0
        if target_score < 5.0:
            target_score = 5.0
        target_band = "Band " + str(target_score)
    avg_str = str(round(avg_score, 1)) if avg_score is not None else "?"
    prompt = (
        "You are an IELTS Writing examiner and top-tier essay coach.\n"
        "The student scored approximately Band " + avg_str + " on this task.\n"
        "Write a realistic " + target_band + " sample essay (" + target_words + " words) that:\n"
        "  - This student could realistically LEARN FROM and grow toward\n"
        "  - Uses " + target_band + "-level vocabulary and grammatical structures (NOT higher - the student must be able to imitate it)\n"
        "  - Matches the original student's task type and question\n"
        "  - Shows concrete techniques that fix the issues listed below\n"
        "  - Demonstrates 2-3 specific sentence-level rewrites from the Must-Fix Sentences section\n\n"
        "**IMPORTANT: Write the essay ENTIRELY in ENGLISH (matching the original student essay language). Do NOT write in Chinese.**\n\n"
        "## Task Question\n" + q + img_ctx + "\n"
        "## Original Student Essay\n" + e + "\n\n"
        "## Per-Dimension Analysis (use these issues to focus your sample)\n" + issues_block + "\n\n"
        "## Must-Fix Sentences (demonstrate these rewrites in your sample)\n" + sent_block + "\n\n"
        "## Output JSON format (strict, no markdown, no prose)\n"
        "{\"essay\": \"<full essay text in English>\", \"improvements\": [\"<key technique 1>\", \"<key technique 2>\", \"<key technique 3>\"]}"
    )
    return prompt
