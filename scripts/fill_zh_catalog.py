#!/usr/bin/env python3
"""Fill remaining zh.json identity stubs with Simplified Chinese Zi Wei terms."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tuvi_mcp" / "i18n" / "zh.json"

STAR_UPDATES = {
    "Tử vi": "紫微",
    "Liêm trinh": "廉贞",
    "Thiên đồng": "天同",
    "Vũ khúc": "武曲",
    "Thái Dương": "太阳",
    "Thiên cơ": "天机",
    "Thiên phủ": "天府",
    "Thái âm": "太阴",
    "Tham lang": "贪狼",
    "Cự môn": "巨门",
    "Thiên tướng": "天相",
    "Thiên lương": "天梁",
    "Thất sát": "七杀",
    "Phá quân": "破军",
    "Thái tuế": "太岁",
    "Thiếu dương": "少阳",
    "Tang môn": "丧门",
    "Thiếu âm": "少阴",
    "Quan phù": "官符",
    "Tử phù": "死符",
    "Tuế phá": "岁破",
    "Long đức": "龙德",
    "Bạch hổ": "白虎",
    "Phúc đức": "福德",
    "Điếu khách": "吊客",
    "Trực phù": "直符",
    "Lộc tồn": "禄存",
    "Bác sỹ": "博士",
    "Lực sĩ": "力士",
    "Thanh long": "青龙",
    "Tiểu hao": "小耗",
    "Tướng quân": "将军",
    "Tấu thư": "奏书",
    "Phi liêm": "飞廉",
    "Hỷ thần": "喜神",
    "Bệnh phù": "病符",
    "Đại hao": "大耗",
    "Phục binh": "伏兵",
    "Tràng sinh": "长生",
    "Mộc dục": "沐浴",
    "Quan đới": "冠带",
    "Lâm quan": "临官",
    "Đế vượng": "帝旺",
    "Suy": "衰",
    "Bệnh": "病",
    "Tử": "死",
    "Mộ": "墓",
    "Tuyệt": "绝",
    "Thai": "胎",
    "Dưỡng": "养",
    "Đà la": "陀罗",
    "Kình dương": "擎羊",
    "Địa không": "地空",
    "Địa kiếp": "地劫",
    "Linh tinh": "铃星",
    "Hỏa tinh": "火星",
    "Văn xương": "文昌",
    "Văn Khúc": "文曲",
    "Thiên khôi": "天魁",
    "Thiên việt": "天钺",
    "Tả phù": "左辅",
    "Hữu bật": "右弼",
    "Long trì": "龙池",
    "Phượng các": "凤阁",
    "Tam thai": "三台",
    "Bát tọa": "八座",
    "Ân quang": "恩光",
    "Thiên quý": "天贵",
    "Thiên khốc": "天哭",
    "Thiên hư": "天虚",
    "Thiên đức": "天德",
    "Nguyệt đức": "月德",
    "Thiên hình": "天刑",
    "Thiên riêu": "天姚",
    "Thiên y": "天医",
    "Quốc ấn": "国印",
    "Đường phù": "堂符",
    "Đào hoa": "桃花",
    "Hồng loan": "红鸾",
    "Thiên hỷ": "天喜",
    "Thiên giải": "天解",
    "Địa giải": "地解",
    "Giải thần": "解神",
    "Thai phụ": "台辅",
    "Phong cáo": "封诰",
    "Thiên tài": "天才",
    "Thiên thọ": "天寿",
    "Thiên thương": "天伤",
    "Thiên sứ": "天使",
    "Thiên la": "天罗",
    "Địa võng": "地网",
    "Hóa khoa": "化科",
    "Hóa quyền": "化权",
    "Hóa lộc": "化禄",
    "Hóa kỵ": "化忌",
    "Cô thần": "孤辰",
    "Quả tú": "寡宿",
    "Thiên mã": "天马",
    "Phá toái": "破碎",
    "Thiên quan": "天官",
    "Thiên phúc": "天福",
    "Lưu hà": "流霞",
    "Thiên trù": "天厨",
    "Kiếp sát": "劫杀",
    "Hoa cái": "华盖",
    "LN. Văn tinh": "流年文星",
    "Đẩu quân": "斗君",
    "Thiên không": "天空",
    "Văn khúc": "文曲",
    "HẢI TRUNG KIM": "海中金",
    "GIÁNG HẠ THỦY": "涧下水",
    "TÍCH LỊCH HỎA": "霹雳火",
    "BÍCH THƯỢNG THỔ": "壁上土",
    "TANG ÐỐ MỘC": "桑柘木",
    "ÐẠI KHÊ THỦY": "大溪水",
    "LƯ TRUNG HỎA": "炉中火",
    "THÀNH ÐẦU THỔ": "城头土",
    "TÒNG BÁ MỘC": "松柏木",
    "KIM BẠCH KIM": "金箔金",
    "PHÚ ÐĂNG HỎA": "覆灯火",
    "SA TRUNG THỔ": "沙中土",
    "ÐẠI LÂM MỘC": "大林木",
    "BẠCH LẠP KIM": "白蜡金",
    "TRƯỜNG LƯU THỦY": "长流水",
    "SA TRUNG KIM": "沙中金",
    "THIÊN HÀ THỦY": "天河水",
    "THIÊN THƯỢNG HỎA": "天上火",
    "LỘ BÀN THỔ": "路旁土",
    "DƯƠNG LIỄU MỘC": "杨柳木",
    "TRUYỀN TRUNG THỦY": "泉中水",
    "SƠN HẠ HỎA": "山下火",
    "ÐẠI TRẠCH THỔ": "大驿土",
    "THẠCH LỰU MỘC": "石榴木",
    "KIẾM PHONG KIM": "剑锋金",
    "SƠN ÐẦU HỎA": "山头火",
    "ỐC THƯỢNG THỔ": "屋上土",
    "BÌNH ÐỊA MỘC": "平地木",
    "XOA XUYẾN KIM": "钗钏金",
    "ÐẠI HẢI THỦY": "大海水",
    "Kim tứ Cục": "金四局",
    "Mộc tam Cục": "木三局",
    "Thủy nhị Cục": "水二局",
    "Hỏa lục Cục": "火六局",
    "Thổ ngũ Cục": "土五局",
    "Miếu": "庙",
    "Vượng": "旺",
    "Đắc": "得",
    "Bình": "平",
    "Hãm": "陷",
    "L.Thái Tuế": "流太岁",
    "L.Lộc Tồn": "流浪存",
    "L.Kình Dương": "流擎羊",
    "L.Đà La": "流陀罗",
    "L.Thiên Mã": "流天马",
    "L.Thiên Khốc": "流天哭",
    "L.Thiên Hư": "流天虚",
}


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    missing = [k for k in STAR_UPDATES if k not in data["stars"]]
    extra = [k for k in data["stars"] if k not in STAR_UPDATES]
    if missing or extra:
        raise SystemExit(f"star key mismatch missing={missing[:10]} extra={extra[:10]}")
    data["stars"].update(STAR_UPDATES)
    data["chi"]["Tí"] = "子"
    data["chi"]["Mẹo"] = "卯"
    data["chi"]["Tị"] = "巳"
    data["can_abbr"] = {
        "Giáp": "甲.",
        "Ất": "乙.",
        "Bính": "丙.",
        "Đinh": "丁.",
        "Mậu": "戊.",
        "Kỷ": "己.",
        "Canh": "庚.",
        "Tân": "辛.",
        "Nhâm": "壬.",
        "Quý": "癸.",
    }
    data["brightness_abbrev"]["Miếu địa"] = "庙"
    data["brightness_abbrev"]["Vượng địa"] = "旺"
    data["brightness_abbrev"]["Đắc địa"] = "得"
    data["brightness_abbrev"]["Bình hòa"] = "平"
    data["brightness_abbrev"]["Hãm địa"] = "陷"
    data["gender"]["Nam"] = "男"
    data["gender"]["Nữ"] = "女"
    data["am_duong"]["Dương"] = "阳"
    data["am_duong"]["Âm"] = "阴"
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {PATH}")


if __name__ == "__main__":
    main()
