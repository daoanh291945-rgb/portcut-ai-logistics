from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium


# =========================================================
# 1. CẤU HÌNH ỨNG DỤNG
# =========================================================

st.set_page_config(
    page_title="PortCut AI | Dự báo rủi ro cut-off",
    page_icon="🚢",
    layout="wide",
)

st.title("🚢 PortCut AI — Dự báo và quản trị rủi ro trễ cut-off")
st.caption(
    "Công cụ thử nghiệm hỗ trợ đánh giá nguy cơ container đến cảng trễ cut-off. "
    "Kết quả là ước tính hỗ trợ ra quyết định, không thay thế xác nhận của hãng tàu, "
    "đại lý hoặc cảng."
)


PORTS = {
    "Cảng Hải Phòng": {"lat": 20.8449, "lon": 106.6881},
    "Đình Vũ": {"lat": 20.8298, "lon": 106.8005},
    "Chùa Vẽ": {"lat": 20.8657, "lon": 106.7150},
    "Tân Vũ": {"lat": 20.8190, "lon": 106.8050},
    "Cảng Cái Mép": {"lat": 10.5140, "lon": 107.0130},
    "Cảng Cát Lái": {"lat": 10.7628, "lon": 106.7930},
    "Cảng Đà Nẵng": {"lat": 16.1256, "lon": 108.2130},
    "Khác / tự nhập tọa độ": None,
}


# =========================================================
# 2. THIẾT LẬP CẢNG
# =========================================================

with st.sidebar:
    st.header("⚙️ Thiết lập chuyến hàng")

    port_name = st.selectbox(
        "Cảng đích",
        list(PORTS.keys()),
        index=4,
    )

    if PORTS[port_name] is None:
        port_lat = st.number_input(
            "Vĩ độ cảng",
            min_value=-90.0,
            max_value=90.0,
            value=10.5,
            format="%.5f",
        )

        port_lon = st.number_input(
            "Kinh độ cảng",
            min_value=-180.0,
            max_value=180.0,
            value=107.0,
            format="%.5f",
        )
    else:
        port_lat = PORTS[port_name]["lat"]
        port_lon = PORTS[port_name]["lon"]

    st.caption(
        "Tọa độ mặc định đại diện khu vực cảng, "
        "không bảo đảm trùng cổng tiếp nhận container."
    )


# =========================================================
# 3. LẤY VÀ PHÂN TÍCH THỜI TIẾT
# =========================================================

def get_weather(lat, lon):
    """Lấy thời tiết từ Open-Meteo, không cần API key."""

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,precipitation,"
            "rain,wind_speed_10m,weather_code"
        ),
        "forecast_days": 2,
        "timezone": "Asia/Bangkok",
    }

    response = requests.get(
        url,
        params=params,
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


def weather_summary(weather):
    current = weather.get("current", {})

    code = current.get("weather_code")

    code_text = {
        0: "Trời quang",
        1: "Ít mây",
        2: "Có mây",
        3: "Nhiều mây",
        45: "Sương mù",
        48: "Sương mù đóng băng",
        51: "Mưa phùn nhẹ",
        53: "Mưa phùn vừa",
        55: "Mưa phùn dày",
        61: "Mưa nhẹ",
        63: "Mưa vừa",
        65: "Mưa lớn",
        71: "Tuyết nhẹ",
        73: "Tuyết vừa",
        75: "Tuyết lớn",
        80: "Mưa rào nhẹ",
        81: "Mưa rào vừa",
        82: "Mưa rào mạnh",
        95: "Dông",
        96: "Dông có mưa đá",
        99: "Dông mạnh",
    }.get(code, f"Mã thời tiết {code}")

    rain = float(current.get("precipitation", 0) or 0)
    wind = float(current.get("wind_speed_10m", 0) or 0)

    score = 0
    reasons = []

    if rain >= 5:
        score += 20
        reasons.append(f"Lượng mưa hiện tại {rain:.1f} mm")
    elif rain >= 1:
        score += 10
        reasons.append(f"Có mưa ({rain:.1f} mm)")

    if wind >= 40:
        score += 20
        reasons.append(f"Gió mạnh {wind:.0f} km/h")
    elif wind >= 25:
        score += 10
        reasons.append(f"Gió tương đối mạnh {wind:.0f} km/h")

    if code in [45, 48, 65, 75, 82, 95, 96, 99]:
        score += 15
        reasons.append(code_text)

    return {
        "description": code_text,
        "temperature": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "rain": rain,
        "wind": wind,
        "score": min(score, 40),
        "reasons": reasons,
    }


# =========================================================
# 4. PHƯƠNG ÁN XỬ LÝ RỦI RO
# =========================================================

def build_recommendations(
    buffer_hours,
    weather_score,
    traffic_level,
    port_wait,
    cargo_type,
):
    actions = []

    if buffer_hours < 0:
        actions.extend([
            (
                "Ưu tiên 1",
                "Liên hệ ngay hãng tàu/đại lý để xác nhận cut-off thực tế, "
                "khả năng gia hạn và chuyến thay thế.",
            ),
            (
                "Ưu tiên 2",
                "Kiểm tra khả năng điều xe thay thế hoặc tuyến khác. "
                "Chỉ thực hiện sau khi điều độ xác nhận tính khả thi.",
            ),
            (
                "Ưu tiên 3",
                "Thông báo các bên liên quan và chuẩn bị phương án chuyển chuyến "
                "nếu không thể vào cảng đúng hạn.",
            ),
        ])

    elif buffer_hours < 2:
        actions.extend([
            (
                "Ưu tiên 1",
                "Theo dõi ETA sát sao, xác minh tiến độ với tài xế và điều độ.",
            ),
            (
                "Ưu tiên 2",
                "Kiểm tra tuyến thay thế hoặc xe dự phòng. "
                "Chỉ đổi phương án khi thời gian tiết kiệm đủ bù thời gian chuyển đổi.",
            ),
        ])

    elif buffer_hours < 5:
        actions.extend([
            (
                "Ưu tiên 1",
                "Cập nhật ETA định kỳ và xác minh giao thông trước khi xe đến cảng.",
            ),
            (
                "Ưu tiên 2",
                "Chuẩn bị phương án dự phòng nếu thời gian chờ cổng tăng.",
            ),
        ])

    else:
        actions.append((
            "Ưu tiên 1",
            "Duy trì kế hoạch hiện tại và cập nhật ETA nếu điều kiện thay đổi.",
        ))

    if weather_score >= 15:
        actions.append((
            "Thời tiết",
            "Kiểm tra cảnh báo thời tiết dọc tuyến và xác minh điều kiện "
            "vận hành an toàn với đơn vị vận tải.",
        ))

    if traffic_level >= 3:
        actions.append((
            "Giao thông",
            "Xác minh ùn tắc với tài xế hoặc nguồn giao thông thực tế. "
            "Mức giao thông nhập tay không phải dữ liệu trực tiếp.",
        ))

    if port_wait >= 2:
        actions.append((
            "Cổng cảng",
            "Liên hệ đại lý hoặc đơn vị khai thác để xác minh thời gian chờ "
            "và tình trạng tiếp nhận container.",
        ))

    cargo_text = str(cargo_type).lower()

    if any(word in cargo_text for word in ["reefer", "lạnh", "đông lạnh"]):
        actions.append((
            "Hàng lạnh",
            "Kiểm tra nguồn điện reefer, nhiệt độ cài đặt và phương án "
            "cấp điện dự phòng theo quy trình.",
        ))

    if "kiểm dịch" in cargo_text:
        actions.append((
            "Kiểm dịch",
            "Xác minh hồ sơ, thời gian kiểm tra và yêu cầu kiểm dịch "
            "để tính đủ thời gian trước cut-off.",
        ))

    return actions


# =========================================================
# 5. TẠO CÁC TAB
# =========================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "🔎 Phân tích chuyến hàng",
    "📊 Dữ liệu lịch sử",
    "📍 GPS & tuyến đường",
    "ℹ️ Phạm vi & giới hạn",
])


# =========================================================
# TAB 1: PHÂN TÍCH CHUYẾN HÀNG
# =========================================================

with tab1:

    left, right = st.columns([1.15, 0.85])

    with left:
        st.subheader("Thông tin kế hoạch")

        now = datetime.now().replace(second=0, microsecond=0)

        departure = st.datetime_input(
            "Thời gian xe dự kiến rời kho",
            value=now + timedelta(hours=1),
        )

        cutoff = st.datetime_input(
            "Thời hạn cut-off",
            value=now + timedelta(hours=8),
        )

        travel_hours = st.number_input(
            "Thời gian chạy dự kiến (giờ)",
            min_value=0.1,
            max_value=120.0,
            value=4.0,
            step=0.25,
        )

        buffer_extra = st.number_input(
            "Dự phòng kiểm tra/phát sinh khác (giờ)",
            min_value=0.0,
            max_value=48.0,
            value=1.0,
            step=0.25,
        )

        # SỬA LỖI: selectbox trả về chuỗi, không dùng tuple.
        traffic_label = st.selectbox(
            "Mức độ giao thông (theo thông tin hiện có)",
            [
                "1 - Thông thoáng",
                "2 - Bình thường",
                "3 - Đông",
                "4 - Tắc nghiêm trọng",
            ],
            index=1,
        )

        traffic_value = int(traffic_label[0])

        port_wait = st.number_input(
            "Thời gian chờ cổng dự kiến (giờ)",
            min_value=0.0,
            max_value=24.0,
            value=1.0,
            step=0.25,
        )

        cargo = st.selectbox(
            "Loại hàng",
            [
                "Hàng thường",
                "Hàng lạnh / reefer",
                "Thực phẩm cần kiểm dịch",
                "Khác",
            ],
        )

        analyze = st.button(
            "Dự báo rủi ro",
            type="primary",
            use_container_width=True,
        )

    with right:
        st.subheader("Thời tiết tại khu vực cảng")

        st.caption(
            "Dữ liệu trực tuyến tại tọa độ cảng, "
            "không đại diện toàn bộ tuyến đường."
        )

        if st.button("Lấy thời tiết mới nhất", use_container_width=True):
            try:
                st.session_state["weather_data"] = get_weather(
                    port_lat,
                    port_lon,
                )
                st.session_state["weather_error"] = None
            except Exception:
                st.session_state["weather_error"] = (
                    "Không kết nối được dịch vụ thời tiết."
                )

        if "weather_data" not in st.session_state:
            try:
                st.session_state["weather_data"] = get_weather(
                    port_lat,
                    port_lon,
                )
                st.session_state["weather_error"] = None
            except Exception:
                st.session_state["weather_error"] = (
                    "Không kết nối được dịch vụ thời tiết."
                )

        if st.session_state.get("weather_data"):
            ws = weather_summary(st.session_state["weather_data"])

            a, b = st.columns(2)

            a.metric("Hiện trạng", ws["description"])

            b.metric(
                "Nhiệt độ",
                f"{ws['temperature']} °C"
                if ws["temperature"] is not None
                else "N/A",
            )

            a.metric("Mưa hiện tại", f"{ws['rain']:.1f} mm")
            b.metric("Tốc độ gió", f"{ws['wind']:.0f} km/h")

            if ws["humidity"] is not None:
                st.caption(f"Độ ẩm: {ws['humidity']}%")

            if ws["reasons"]:
                st.warning(
                    "Tín hiệu thời tiết cần lưu ý: "
                    + "; ".join(ws["reasons"])
                )
            else:
                st.success(
                    "Chưa phát hiện tín hiệu thời tiết rủi ro cao "
                    "theo ngưỡng thử nghiệm."
                )

        else:
            ws = {"score": 0, "reasons": []}

            st.info(
                st.session_state.get(
                    "weather_error",
                    "Chưa có dữ liệu thời tiết.",
                )
            )

    if analyze:

        # Không phân tích khi cut-off sớm hơn thời gian rời kho.
        if cutoff <= departure:
            st.error(
                "Thời hạn cut-off phải sau thời gian xe dự kiến rời kho. "
                "Hãy kiểm tra lại hai mốc thời gian."
            )

        else:
            ws = (
                weather_summary(st.session_state["weather_data"])
                if st.session_state.get("weather_data")
                else {"score": 0, "reasons": []}
            )

            eta = departure + timedelta(
                hours=(
                    float(travel_hours)
                    + float(buffer_extra)
                    + float(port_wait)
                )
            )

            buffer_hours = (cutoff - eta).total_seconds() / 3600

            score = 0
            drivers = []

            if buffer_hours < 0:
                score += 60
                drivers.append("ETA dự kiến sau cut-off")

            elif buffer_hours < 1:
                score += 45
                drivers.append("Thời gian dự phòng dưới 1 giờ")

            elif buffer_hours < 2:
                score += 30
                drivers.append("Thời gian dự phòng dưới 2 giờ")

            elif buffer_hours < 4:
                score += 15
                drivers.append("Thời gian dự phòng còn hạn chế")

            traffic_points = {
                1: 0,
                2: 5,
                3: 15,
                4: 25,
            }

            score += traffic_points[traffic_value]

            if traffic_value >= 3:
                drivers.append(
                    f"Giao thông được nhập ở mức: {traffic_label}"
                )

            score += int(ws["score"])

            if ws["reasons"]:
                drivers.extend(ws["reasons"])

            if port_wait >= 2:
                score += 10
                drivers.append(
                    f"Thời gian chờ cổng dự kiến {port_wait:.1f} giờ"
                )

            score = min(100, score)

            level = (
                "Cao"
                if score >= 60
                else "Trung bình"
                if score >= 30
                else "Thấp"
            )

            st.markdown("---")
            st.subheader("Kết quả dự báo")

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "ETA ước tính",
                eta.strftime("%d/%m/%Y %H:%M"),
            )

            c2.metric(
                "Thời gian còn trước cut-off",
                f"{buffer_hours:.1f} giờ",
            )

            c3.metric(
                "Điểm rủi ro thử nghiệm",
                f"{score}/100",
            )

            c4.metric("Mức rủi ro", level)

            if buffer_hours < 0:
                st.error(
                    "Theo dữ liệu đầu vào, chuyến có nguy cơ đến sau cut-off. "
                    "Cần xác minh ngay với điều độ và hãng tàu/đại lý."
                )

            elif score >= 60:
                st.error(
                    "Rủi ro cao theo bộ quy tắc thử nghiệm. "
                    "Cần xác minh dữ liệu trước khi quyết định."
                )

            elif score >= 30:
                st.warning(
                    "Có yếu tố rủi ro. Cần theo dõi ETA và chuẩn bị "
                    "phương án dự phòng."
                )

            else:
                st.success(
                    "Rủi ro thấp theo thông tin hiện có. "
                    "Tiếp tục theo dõi khi điều kiện thay đổi."
                )

            with st.expander(
                "Vì sao hệ thống đánh giá như vậy?",
                expanded=True,
            ):
                if drivers:
                    for driver in drivers:
                        st.write("• " + driver)
                else:
                    st.write(
                        "Chưa phát hiện yếu tố rủi ro nổi bật "
                        "theo ngưỡng thử nghiệm."
                    )

            st.subheader("Phương án đề xuất")

            recommendations = build_recommendations(
                buffer_hours,
                ws["score"],
                traffic_value,
                port_wait,
                cargo,
            )

            for priority, action in recommendations:
                st.write(f"**{priority}:** {action}")

            result = pd.DataFrame([{
                "thoi_gian_phan_tich": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "cang_dich": port_name,
                "departure": departure.strftime("%Y-%m-%d %H:%M"),
                "cutoff": cutoff.strftime("%Y-%m-%d %H:%M"),
                "eta_uoc_tinh": eta.strftime("%Y-%m-%d %H:%M"),
                "buffer_hours": round(buffer_hours, 2),
                "risk_score_prototype": score,
                "risk_level": level,
                "traffic_input": traffic_label,
                "weather_signal": "; ".join(ws["reasons"]),
                "cargo_type": cargo,
                "drivers": "; ".join(drivers),
            }])

            st.download_button(
                "Tải kết quả phân tích CSV",
                result.to_csv(index=False).encode("utf-8-sig"),
                file_name="ket_qua_du_bao_cutoff.csv",
                mime="text/csv",
            )


# =========================================================
# TAB 2: DỮ LIỆU LỊCH SỬ
# =========================================================

with tab2:

    st.subheader("📊 Tải dữ liệu lịch sử")

    st.write(
        "Tải file Excel hoặc CSV để kiểm tra dữ liệu chuyến hàng. "
        "Bản hiện tại chưa tự huấn luyện mô hình máy học."
    )

    uploaded = st.file_uploader(
        "Chọn file Excel hoặc CSV",
        type=["xlsx", "xls", "csv"],
        key="history_file",
    )

    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            st.success(
                f"Đã đọc {len(df):,} dòng và {len(df.columns)} cột."
            )

            st.write(
                "**Các cột tìm thấy:**",
                ", ".join(map(str, df.columns)),
            )

            st.dataframe(
                df.head(100),
                use_container_width=True,
            )

            st.download_button(
                "Tải dữ liệu đã đọc lại dạng CSV",
                df.to_csv(index=False).encode("utf-8-sig"),
                file_name="du_lieu_da_doc.csv",
                mime="text/csv",
            )

            st.info(
                "Cần xác định các cột thời gian rời kho, cut-off, "
                "thời gian vận chuyển và kết quả đúng hạn/trễ trước khi "
                "xây dựng mô hình dự báo có kiểm định."
            )

        except Exception as e:
            st.error(f"Không đọc được tệp: {e}")

    st.markdown("#### Mẫu cột tham khảo")

    st.code(
        "shipment_id, warehouse_departure, cutoff_time, "
        "planned_travel_hours, traffic_level, weather_level, "
        "port_wait_hours, cargo_type, outcome",
        language="text",
    )


# =========================================================
# TAB 3: TỌA ĐỘ VÀ TUYẾN ĐƯỜNG
# =========================================================

with tab3:

    st.subheader("📍 Xác định vị trí và tính tuyến đường")

    st.warning(
        "Bản này dùng tọa độ nhập thủ công, không tự lấy GPS của trình duyệt. "
        "Tọa độ mặc định chỉ là ví dụ, không phải vị trí thực của người dùng."
    )

    gps_col, route_col = st.columns(2)

    with gps_col:

        st.markdown("#### 1. Điểm xuất phát")

        origin_lat_input = st.number_input(
            "Vĩ độ điểm xuất phát",
            min_value=-90.0,
            max_value=90.0,
            value=float(st.session_state.get("gps_lat", 10.7769)),
            format="%.6f",
            key="origin_lat_input",
        )

        origin_lon_input = st.number_input(
            "Kinh độ điểm xuất phát",
            min_value=-180.0,
            max_value=180.0,
            value=float(st.session_state.get("gps_lon", 106.7009)),
            format="%.6f",
            key="origin_lon_input",
        )

        if st.button(
            "Lưu tọa độ xuất phát",
            use_container_width=True,
        ):
            st.session_state["gps_lat"] = origin_lat_input
            st.session_state["gps_lon"] = origin_lon_input

            st.success("Đã lưu tọa độ xuất phát.")

        st.caption(
            "Có thể lấy tọa độ từ ứng dụng bản đồ. "
            "Hãy nhập tọa độ thực tế nếu muốn tính tuyến có ý nghĩa."
        )

    with route_col:

        st.markdown("#### 2. Tính tuyến đường đến cảng")

        st.write(f"**Cảng đích:** {port_name}")
        st.write(
            f"**Tọa độ cảng:** {port_lat:.5f}, {port_lon:.5f}"
        )

        if st.button(
            "Tính tuyến đường đến cảng",
            type="primary",
            use_container_width=True,
        ):

            origin_lat = st.session_state.get(
                "gps_lat",
                origin_lat_input,
            )

            origin_lon = st.session_state.get(
                "gps_lon",
                origin_lon_input,
            )

            try:
                route_url = (
                    "https://router.project-osrm.org/route/v1/driving/"
                    f"{origin_lon},{origin_lat};{port_lon},{port_lat}"
                )

                response = requests.get(
                    route_url,
                    params={
                        "overview": "full",
                        "geometries": "geojson",
                        "steps": "false",
                    },
                    timeout=25,
                )

                response.raise_for_status()
                route_json = response.json()

                if (
                    route_json.get("code") != "Ok"
                    or not route_json.get("routes")
                ):
                    st.error(
                        "Không tìm được tuyến đường. "
                        "Kiểm tra tọa độ hoặc thử lại sau."
                    )

                else:
                    st.session_state["osrm_route"] = route_json["routes"][0]

                    st.session_state["osrm_origin"] = [
                        origin_lat,
                        origin_lon,
                    ]

                    st.session_state["osrm_destination"] = [
                        port_lat,
                        port_lon,
                    ]

                    st.session_state["osrm_port_name"] = port_name

                    st.session_state["osrm_route_error"] = None

            except Exception:
                st.error(
                    "Không kết nối được dịch vụ định tuyến. "
                    "Kiểm tra mạng hoặc thử lại sau."
                )

    if (
        st.session_state.get("osrm_route")
        and st.session_state.get("osrm_origin")
    ):

        route = st.session_state["osrm_route"]
        origin = st.session_state["osrm_origin"]
        destination = st.session_state["osrm_destination"]

        distance_km = route["distance"] / 1000
        drive_hours = route["duration"] / 3600

        r1, r2, r3 = st.columns(3)

        r1.metric(
            "Khoảng cách tham khảo",
            f"{distance_km:.1f} km",
        )

        r2.metric(
            "Thời gian lái xe ước tính",
            f"{drive_hours:.1f} giờ",
        )

        r3.metric(
            "Nguồn tuyến đường",
            "OSRM / OpenStreetMap",
        )

        st.caption(
            "Thời gian OSRM không phải dữ liệu giao thông trực tiếp. "
            "Chưa bao gồm nghỉ ngơi, chờ cổng, kiểm tra, hạn chế xe tải "
            "hoặc điều kiện vận hành thực tế."
        )

        route_map = folium.Map(
            location=origin,
            zoom_start=8,
            control_scale=True,
        )

        folium.Marker(
            origin,
            tooltip="Điểm xuất phát",
            popup="Điểm xuất phát đã nhập",
            icon=folium.Icon(
                color="blue",
                icon="info-sign",
            ),
        ).add_to(route_map)

        folium.Marker(
            destination,
            tooltip=st.session_state.get(
                "osrm_port_name",
                port_name,
            ),
            popup=st.session_state.get(
                "osrm_port_name",
                port_name,
            ),
            icon=folium.Icon(
                color="red",
                icon="flag",
            ),
        ).add_to(route_map)

        coordinates = route.get(
            "geometry",
            {},
        ).get(
            "coordinates",
            [],
        )

        if coordinates:
            folium.PolyLine(
                [(lat, lon) for lon, lat in coordinates],
                tooltip="Tuyến đường tham khảo",
                weight=5,
            ).add_to(route_map)

        st_folium(
            route_map,
            use_container_width=True,
            height=450,
            returned_objects=[],
        )

        st.markdown("#### 3. Thời tiết tại điểm xuất phát")

        if st.button("Lấy thời tiết tại điểm xuất phát"):

            try:
                live_weather = get_weather(
                    origin[0],
                    origin[1],
                )

                st.session_state["origin_weather"] = weather_summary(
                    live_weather
                )

                st.session_state["origin_weather_error"] = None

            except Exception:
                st.session_state["origin_weather_error"] = True

        if st.session_state.get("origin_weather"):

            live_summary = st.session_state["origin_weather"]

            w1, w2, w3, w4 = st.columns(4)

            w1.metric(
                "Thời tiết",
                live_summary["description"],
            )

            w2.metric(
                "Nhiệt độ",
                f"{live_summary['temperature']} °C"
                if live_summary["temperature"] is not None
                else "N/A",
            )

            w3.metric(
                "Mưa",
                f"{live_summary['rain']:.1f} mm",
            )

            w4.metric(
                "Gió",
                f"{live_summary['wind']:.0f} km/h",
            )

            if live_summary["reasons"]:
                st.warning(
                    "Tín hiệu thời tiết cần lưu ý: "
                    + "; ".join(live_summary["reasons"])
                )

        elif st.session_state.get("origin_weather_error"):
            st.info(
                "Chưa lấy được thời tiết tại điểm xuất phát. "
                "Thử lại sau."
            )


# =========================================================
# TAB 4: GIỚI HẠN HỆ THỐNG
# =========================================================

with tab4:

    st.subheader("Minh bạch về dữ liệu và giới hạn")

    st.markdown("""
**1. Thời tiết**
- Lấy dữ liệu qua Open-Meteo API.
- Dữ liệu tại tọa độ được chọn, không đại diện toàn bộ tuyến đường.

**2. Tuyến đường**
- Sử dụng OSRM/OpenStreetMap để tính tuyến tham khảo.
- Thời gian ước tính không phải dữ liệu ùn tắc thời gian thực.

**3. Giao thông**
- Mức độ giao thông do người dùng nhập.
- Chưa kết nối nguồn giao thông trực tiếp.

**4. GPS**
- Phiên bản hiện tại sử dụng tọa độ nhập thủ công.
- Chưa tự theo dõi vị trí xe container.

**5. Lịch tàu và cut-off**
- Cần xác minh từ booking hoặc thông báo cập nhật của hãng tàu/đại lý.

**6. Dự báo rủi ro**
- Điểm 0–100 hiện là bộ quy tắc thử nghiệm.
- Đây chưa phải xác suất thống kê hoặc mô hình máy học đã huấn luyện.
- Cần dữ liệu lịch sử có nhãn kết quả và kiểm thử trước khi công bố độ chính xác.

**7. Quyết định vận hành**
- Các phương án chỉ là gợi ý.
- Nhân viên cần xác minh với điều độ, cảng, hãng tàu và khách hàng trước khi thực hiện.
""")

    st.markdown(
        "Nguồn thời tiết: https://open-meteo.com/en/docs"
    )


st.markdown("---")

st.caption(
    "Prototype VYLT 2026 • Dùng cho mục đích thử nghiệm. "
    "Cần kiểm chứng dữ liệu và quy trình trước khi áp dụng thực tế."
)
