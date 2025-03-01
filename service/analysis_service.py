from rest_framework.exceptions import ValidationError

from app.analysis.apriori import *
from app.dao.ESDao import *
from app.dao.dao import *


def getMaxRelated(rules):
    max_rules = []
    max = 0
    for i in range(len(rules)):
        item = rules[i]
        if item[2] >= max:
            max = item[2]
    for item in rules:
        if item[2] is max:
            item[0] = list(item[0])
            item[1] = list(item[1])
            max_rules.append(item)
    return max_rules


def convert(grade):
    if grade is "A":
        return 100
    if grade is "A-":
        return 89
    if grade is "B+":
        return 84
    if grade is "B":
        return 80
    if grade is "B-":
        return 77
    if grade is "C+":
        return 74
    if grade is "C":
        return 71
    if grade is "C-":
        return 67
    if grade is "D+":
        return 64
    if grade is "D":
        return 62
    if grade is "F":
        return 59
    raise ValidationError("成绩错误")


def getStudentGrade(expected):
    """五级课程"""
    course_ids = getCoursesByScoreMethod(1)
    grade_five = getStuIdAndScoreByCourseId(course_ids)
    for item in grade_five:
        item["grade"] = convert(item["grade"])

    """百分课程"""
    course_ids = getCoursesByScoreMethod()
    grade_hun = getStuIdAndScoreByCourseId(course_ids)
    grades = grade_hun + grade_five
    grade_dict = {}
    for item in grades:
        # 成绩大于计算分析的期望值 五级制比如为B A
        if item["grade"] >= expected:
            key = item["stuId"]
            grade = item["grade"]
            if item["stuId"] not in grade_dict:
                value = [grade]
                grade_dict[key] = value
            else:
                grade_dict[key].append(grade)
    grade_list = []
    for (k, v) in grade_dict.items():
        grade_list.append(v)
    return grade_list


# 返回五级制中课程存在的关联关系和百分制课程关联关系
def getStudentClassGradesRelatedRules():
    grade = getStudentGrade("80")

    try:
        L, suppData = apriori(grade)
        rules = generateRules(L, suppData, minConf=0.5)
    except BaseException as E:
        raise BaseException("关联分析时出现错误")

    max_rules = getMaxRelated(rules)
    course_rules = []
    for item in max_rules:
        course_rule_item = (
            getCourseById(item[0]),
            getCourseById(item[1]),
            item[2]
        )
        course_rules.append(course_rule_item)
    return course_rules


def mul(a, b):
    sum_ab = 0.0
    for i in range(len(a)):
        temp = a[i] * b[i]
        sum_ab += temp
    return sum_ab


# 计算皮尔逊相关系数 因果是相关 相关不一定是因果 相关系数表示因果关系的程度  不是相关关系可以使用关联分析
def getPcc(x, y):
    if len(x) is not len(y):
        raise ValidationError("两组数据集大小不一致")
    n = len(x)
    # 求和
    sum1 = sum(x)
    sum2 = sum(y)
    # 求乘积之和
    sum_xy = mul(x, y)
    # 求平方和
    sum_xx = sum([pow(i, 2) for i in x])
    sum_yy = sum([pow(j, 2) for j in y])
    num = sum_xy - (float(sum1) * float(sum2) / n)
    den = sqrt((sum_xx - float(sum1 ** 2) / n) * (sum_yy - float(sum2 ** 2) / n))
    return num / den


def teacherEvaLowGradeList():
    lowList = getTeacherEvaLowGradeList()
    data = []
    for item in lowList:
        data.append(item['_source'])
    return data


def analysisGraduationPointAll(stu_level):
    """ 整个学院的毕业要求指标点统计分析
    :return:
    """
    result = []
    # 获取所有的毕业要求
    requirements = getGraduationRequirementList()
    for target in requirements:
        result_item = {"desc": target['name']}
        target_id = target['id']
        point_ids = getGraduationPoints(target_id)
        target_results = getStudentTargetResultsById(stu_level, point_ids)
        point_infos = []
        target_avg = 0
        for target_item in target_results:
            desc = getGraduationPointInfo(target_item['id'])['description']
            complete_percent = target_item['percent']
            target_avg += complete_percent
            temp = {'id': target_item['id'], 'desc': desc, 'value': complete_percent}
            point_infos.append(temp)
        target_avg = target_avg / len(point_infos)
        result_item['point'] = point_infos
        result_item['avg'] = target_avg
        result.append(result_item)
    return result


def analysisGraduationPointStudent(student_id):
    result = []
    # 获取所有的毕业要求
    requirements = getGraduationRequirementList()
    for target in requirements:
        result_item = {"desc": target['name']}
        target_id = target['id']
        point_ids = getGraduationPoints(target_id)
        target_results = getGraduationTarget(student_id, point_ids)
        point_infos = []
        target_avg = 0
        for target_item in target_results:
            desc = getGraduationPointInfo(target_item['id'])['description']
            complete_percent = target_item['percent']
            target_avg += complete_percent
            temp = {'id': target_item['id'], 'desc': desc, 'value': complete_percent}
            point_infos.append(temp)
        target_avg = target_avg / len(point_infos)
        result_item['point'] = point_infos
        result_item['avg'] = target_avg
        result.append(result_item)
    return result


def getStudentTargetCourse(target_id):
    result = []
    point_course = getPointCourses(target_id)
    for item in point_course:
        result_item = {'course_id': item['course_id'], 'proportion': item['proportion'],
                       'expected_score': item['expected_score']}
        course_id = item['course_id']
        courseInfo = getCourseById(course_id)
        result_item['course_name'] = courseInfo['course_name']
        result_item['course_number'] = courseInfo['course_number']
        result.append(result_item)
    return result


def getGraduationTargetList():
    targetList = graduationPointList
    return targetList


def analysisGraduationTarget(target_id):
    points_ids = getGraduationPoints(target_id)
    points_result = getGraduationPointFinishedRatioByPointIds(points_ids)
    result = []
    for index, item in enumerate(points_result):
        point_desc = getGraduationPointInfo(item['point_id'])
        result_item = {'id': index, 'percent': item['percent'], 'desc': point_desc}
        result.append(result_item)
    return result


if __name__ == '__main__':
    print(teacherEvaLowGradeList())
