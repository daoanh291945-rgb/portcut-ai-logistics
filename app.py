import io
import math
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(page_title="PortCut AI | Dự báo rủi ro cut-off", page_icon="🚢", layout="wide")

# Coordinates are approximate area-level coordinates, not terminal gates.
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

st.title("🚢 PortCut AI — Dự báo và quản trị rủi ro trễ cut-off")
st.caption("Bản thử nghiệm hỗ trợ nhân viên logistics ra quyết định. Dữ liệu thời tiết lấy từ API Open-Meteo; kết quả dự báo là ước tính, không thay thế xác nhận của cảng/hãng tàu.")

with st.sidebar:
    st.header("Thiết lập chuyến hàng")
    port_name = st.selectbox("Cảng đích", list(PORTS.keys()), index=4)
    if port_name == "Khác / tự nhập tọa độ":
        port_lat = st.number_input("Vĩ độ cảng", min_value=-90.0, max_value=90.0, value=10.5, format="%.5f")
        port_lon = st.number_input("Kinh độ cảng", min_value=-180.0, max_value=180.0, value=107.0, format="%.5f")
    else:
        port_lat = PORTS[port_name]["lat"]
        port_lon = PORTS[port_name]["lon"]
    st.markdown("---")
    st.caption("Tọa độ cảng mặc định chỉ đại diện khu vực cảng. Có thể nhập tọa độ chính xác nếu biết vị trí cổng/terminal.")


def get_weather(lat, lon):
    """Fetch current conditions and forecast from Open-Meteo; no API key required."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m,weather_code",
        "hourly": "precipitation_probability,precipitation,wind_speed_10m,weather_code",
        "forecast_days": 2,
        "timezone": "Asia/Bangkok",
    }
    response = requests.get(url, params=params, timeout=12)
    response.raise_for_status()
    return response.json()


def weather_summary(weather):
    current = weather.get("current", {})
    code = current.get("weather_code")
    code_text = {
        0: "Trời quang", 1: "Ít mây", 2: "Có mây", 3: "Nhiều mây",
        45: "Sương mù", 48: "Sương mù đóng băng", 51: "Mưa phùn nhẹ",
        53: "Mưa phùn vừa", 55: "Mưa phùn dày", 61: "Mưa nhẹ",
        63: "Mưa vừa", 65: "Mưa lớn", 71: "Tuyết nhẹ", 73: "Tuyết vừa",
        75: "Tuyết lớn", 80: "Mưa rào nhẹ", 81: "Mưa rào vừa",
        82: "Mưa rào mạnh", 95: "Dông", 96: "Dông có mưa đá", 99: "Dông mạnh",
    }.get(code, f"Mã thời tiết {code}")
    rain = float(current.get("precipitation", 0) or 0)
    wind = float(current.get("wind_speed_10m", 0) or 0)
    # Transparent heuristic: weather is a risk signal, not a certified travel-delay model.
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
    return {"description": code_text, "temperature": current.get("temperature_2m"), "humidity": current.get("relative_humidity_2m"), "rain": rain, "wind": wind, "score": min(score, 40), "reasons": reasons}


def find_col(df, candidates):
    normalized = {str(c).strip().lower().replace(" ", "_").replace("-", "_"): c for c in df.columns}
    for candidate in candidates:
        key = candidate.lower().replace(" ", "_").replace("-", "_")
        if key in normalized:
            return normalized[key]
    for c in df.columns:
        s = str(c).strip().lower()
        if any(term in s for term in candidates):
            return c
    return None


def build_recommendations(buffer_hours, weather_score, traffic_level, port_wait, cargo_type):
    actions = []
    if buffer_hours < 0:
        actions.append(("Ưu tiên 1", "Liên hệ ngay hãng tàu/đại lý xác nhận cut-off thực tế, khả năng gia hạn và chuyến thay thế; không tự giả định được gia hạn."))
        actions.append(("Ưu tiên 2", "Kiểm tra khả năng điều xe thay thế hoặc tuyến khác; chỉ thực hiện khi điều độ xác nhận khả thi và tính cả chi phí phát sinh."))
        actions.append(("Ưu tiên 3", "Thông báo khách hàng/đơn vị liên quan và chuẩn bị phương án chuyển chuyến nếu không thể vào cảng đúng hạn."))
    elif buffer_hours < 2:
        actions.append(("Ưu tiên 1", "Theo dõi sát ETA và liên hệ tài xế/điều độ để xác minh tiến độ; báo trước cho đại lý/cảng nếu quy trình cho phép."))
        actions.append(("Ưu tiên 2", "Kiểm tra tuyến thay thế và điều kiện đổi xe ngay, nhưng chỉ đổi khi thời gian tiết kiệm dự kiến lớn hơn thời gian chuyển đổi."))
    elif buffer_hours < 5:
        actions.append(("Ưu tiên 1", "Đặt mốc kiểm tra ETA định kỳ và xác minh tình trạng giao thông/cổng cảng trước khi xe đến."))
        actions.append(("Ưu tiên 2", "Chuẩn bị phương án dự phòng nếu thời gian chờ cổng tăng hoặc thời tiết xấu hơn dự báo."))
    else:
        actions.append(("Ưu tiên 1", "Duy trì kế hoạch hiện tại; cập nhật ETA khi có thay đổi về giao thông, thời tiết hoặc lịch tàu."))
    if weather_score >= 15:
        actions.append(("Thời tiết", "Kiểm tra cảnh báo thời tiết dọc tuyến và xác nhận điều kiện vận hành an toàn với đơn vị vận tải."))
    if traffic_level >= 2:
        actions.append(("Giao thông", "Xác minh tắc đường bằng nguồn thực tế/tài xế; không coi mức giao thông nhập tay là dữ liệu trực tiếp."))
    if port_wait >= 2:
        actions.append(("Cổng cảng", "Gọi đại lý/đơn vị khai thác để xác minh thời gian chờ cổng và tình trạng tiếp nhận container."))
    if "reefer" in str(cargo_type).lower() or "lạnh" in str(cargo_type).lower() or "đông lạnh" in str(cargo_type).lower():
        actions.append(("Hàng lạnh", "Kiểm tra nguồn điện reefer, nhiệt độ cài đặt và phương án cấp điện dự phòng theo quy trình."))
    return actions


tab1, tab2, tab_gps, tab3 = st.tabs(["🔎 Phân tích chuyến hàng", "📊 Dữ liệu lịch sử", "📍 GPS & tuyến đường", "ℹ️ Phạm vi & giới hạn"])

with tab1:
    left, right = st.columns([1.15, 0.85])
    with left:
        st.subheader("Thông tin kế hoạch")
        now = datetime.now().replace(second=0, microsecond=0)
        departure = st.datetime_input("Thời gian xe dự kiến rời kho", value=now + timedelta(hours=1))
        cutoff = st.datetime_input("Thời hạn cut-off", value=now + timedelta(hours=8))
        travel_hours = st.number_input("Thời gian chạy dự kiến (giờ)", min_value=0.1, max_value=120.0, value=4.0, step=0.25)
        buffer_extra = st.number_input("Dự phòng chờ cổng/kiểm tra (giờ)", min_value=0.0, max_value=48.0, value=1.0, step=0.25)
        traffic = st.select_slider("Mức độ giao thông (nhập theo thông tin hiện có)", options=[("1 - Thông thoáng", 1), ("2 - Bình thường", 2), ("3 - Đông", 3), ("4 - Tắc nghiêm trọng", 4)], value=("2 - Bình thường", 2), format_func=lambda x: x[0])
        port_wait = st.number_input("Thời gian chờ cổng dự kiến (giờ)", min_value=0.0, max_value=24.0, value=1.0, step=0.25)
        cargo = st.selectbox("Loại hàng", ["Hàng thường", "Hàng lạnh / reefer", "Thực phẩm cần kiểm dịch", "Khác"])
        analyze = st.button("Dự báo rủi ro", type="primary", use_container_width=True)
    with right:
        st.subheader("Thời tiết tại khu vực cảng")
        st.caption("Dữ liệu API trực tiếp khi có kết nối Internet; phản ánh khu vực cảng, không phải toàn bộ tuyến đường.")
        if st.button("Lấy thời tiết mới nhất", use_container_width=True) or "weather_data" not in st.session_state:
            try:
                st.session_state.weather_data = get_weather(port_lat, port_lon)
                st.session_state.weather_error = None
            except Exception as e:
                st.session_state.weather_error = str(e)
        if st.session_state.get("weather_data"):
            try:
                ws = weather_summary(st.session_state.weather_data)
                a, b = st.columns(2)
                a.metric("Hiện trạng", ws["description"])
                b.metric("Nhiệt độ", f"{ws['temperature']} °C" if ws["temperature"] is not None else "N/A")
                a.metric("Mưa hiện tại", f"{ws['rain']:.1f} mm")
                b.metric("Tốc độ gió", f"{ws['wind']:.0f} km/h")
                st.caption(f"Độ ẩm: {ws['humidity']}%" if ws["humidity"] is not None else "Không có dữ liệu độ ẩm")
                if ws["reasons"]:
                    st.warning("Tín hiệu thời tiết cần lưu ý: " + "; ".join(ws["reasons"]))
                else:
                    st.success("Chưa thấy tín hiệu thời tiết rủi ro cao theo ngưỡng thử nghiệm của ứng dụng.")
            except Exception:
                ws = {"score": 0, "reasons": []}
                st.info("API trả về dữ liệu chưa đủ để hiển thị.")
        else:
            ws = {"score": 0, "reasons": []}
            if st.session_state.get("weather_error"):
                st.warning("Chưa lấy được dữ liệu thời tiết. Kiểm tra Internet hoặc thử tải lại. Chi tiết: " + st.session_state.weather_error)
            else:
                st.info("Nhấn nút để lấy dữ liệu thời tiết.")

    if analyze:
        ws = weather_summary(st.session_state.weather_data) if st.session_state.get("weather_data") else {"score": 0, "reasons": []}
        eta = departure + timedelta(hours=float(travel_hours) + float(buffer_extra) + float(port_wait))
        buffer_hours = (cutoff - eta).total_seconds() / 3600
        # Heuristic risk score for prototype; not a trained/validated ML model.
        score = 0
        drivers = []
        if buffer_hours < 0:
            score += 60
            drivers.append("ETA dự kiến sau cut-off")
        elif buffer_hours < 1:
            score += 45
            drivers.append("Dự phòng trước cut-off dưới 1 giờ")
        elif buffer_hours < 2:
            score += 30
            drivers.append("Dự phòng trước cut-off dưới 2 giờ")
        elif buffer_hours < 4:
            score += 15
            drivers.append("Dự phòng thời gian còn hạn chế")
        traffic_value = traffic[1]
        score += {1: 0, 2: 5, 3: 15, 4: 25}[traffic_value]
        if traffic_value >= 3:
            drivers.append("Giao thông được nhập ở mức đông/tắc")
        score += int(ws["score"])
        if ws["reasons"]:
            drivers.extend(ws["reasons"])
        if port_wait >= 2:
            score += 10
            drivers.append(f"Thời gian chờ cổng dự kiến {port_wait:.1f} giờ")
        score = min(100, score)
        level = "Cao" if score >= 60 else "Trung bình" if score >= 30 else "Thấp"
        st.markdown("---")
        st.subheader("Kết quả dự báo")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ETA ước tính", eta.strftime("%d/%m/%Y %H:%M"))
        c2.metric("Thời gian còn trước cut-off", f"{buffer_hours:.1f} giờ")
        c3.metric("Điểm rủi ro thử nghiệm", f"{score}/100")
        c4.metric("Mức rủi ro", level)
        if buffer_hours < 0:
            st.error("Theo giả định đầu vào, chuyến có nguy cơ đến sau cut-off. Cần xác minh ngay với điều độ và đại lý/hãng tàu.")
        elif score >= 60:
            st.error("Rủi ro cao theo bộ quy tắc thử nghiệm. Cần xác minh các dữ liệu đầu vào trước khi ra quyết định.")
        elif score >= 30:
            st.warning("Có một số yếu tố rủi ro; cần theo dõi ETA và chuẩn bị phương án dự phòng.")
        else:
            st.success("Rủi ro thấp theo các thông tin hiện có; tiếp tục theo dõi nếu điều kiện thay đổi.")
        with st.expander("Vì sao hệ thống đánh giá như vậy?", expanded=True):
            if drivers:
                for d in drivers:
                    st.write("• " + d)
            else:
                st.write("Chưa phát hiện yếu tố rủi ro nổi bật theo ngưỡng thử nghiệm.")
        st.subheader("Phương án đề xuất để nhân viên xem xét")
        for priority, action in build_recommendations(buffer_hours, ws["score"], traffic_value, port_wait, cargo):
            st.write(f"**{priority}:** {action}")
        result = pd.DataFrame([{
            "thoi_gian_phan_tich": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cang_dich": port_name, "departure": departure.strftime("%Y-%m-%d %H:%M"),
            "cutoff": cutoff.strftime("%Y-%m-%d %H:%M"), "eta_uoc_tinh": eta.strftime("%Y-%m-%d %H:%M"),
            "buffer_hours": round(buffer_hours, 2), "risk_score_prototype": score,
            "risk_level": level, "traffic_input": traffic[0], "weather_signal": "; ".join(ws["reasons"]),
            "cargo_type": cargo, "drivers": "; ".join(drivers)
        }])
        st.download_button("Tải kết quả phân tích CSV", result.to_csv(index=False).encode("utf-8-sig"), file_name="ket_qua_du_bao_cutoff.csv", mime="text/csv")

with tab2:
    st.subheader("Tải dữ liệu lịch sử để kiểm tra và phân tích")
    st.write("Tải tệp Excel/CSV chuyến hàng của mày lên. Ứng dụng sẽ đọc và hiển thị dữ liệu; chưa tự huấn luyện mô hình cho đến khi xác định đúng cột kết quả và các trường đầu vào trong file.")
    uploaded = st.file_uploader("Chọn file Excel hoặc CSV", type=["xlsx", "xls", "csv"], key="history_file")
    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            st.success(f"Đã đọc {len(df):,} dòng và {len(df.columns)} cột.")
            st.write("**Các cột tìm thấy:**", ", ".join(map(str, df.columns)))
            st.dataframe(df.head(100), use_container_width=True)
            st.download_button("Tải dữ liệu đã đọc lại dạng CSV", df.to_csv(index=False).encode("utf-8-sig"), file_name="du_lieu_da_doc.csv", mime="text/csv")
            st.info("Bước tiếp theo là ánh xạ cột trong file thực tế (giờ rời kho, cut-off, ETA/thời gian vận chuyển, giao thông, thời tiết, kết quả đúng hạn/trễ) để xây dựng mô hình dự báo có kiểm định. Không nên tự suy đoán cột hoặc tuyên bố độ chính xác khi chưa kiểm thử.")
        except Exception as e:
            st.error(f"Không đọc được tệp: {e}")
    st.markdown("#### Mẫu cột tham khảo (không bắt buộc phải đổi file ngay)")
    st.code("shipment_id, warehouse_departure, cutoff_time, planned_travel_hours, traffic_level, weather_level, port_wait_hours, cargo_type, outcome", language="text")

with tab_gps:
    st.subheader("📍 Định vị GPS bằng điện thoại / máy tính")
    st.write("Cho phép trình duyệt truy cập vị trí để lấy tọa độ thiết bị hiện tại. Khi mở website trên điện thoại, hãy bật GPS và cấp quyền vị trí. Trên Streamlit Community Cloud, trang được chạy qua HTTPS nên trình duyệt có thể yêu cầu quyền định vị.")
    st.warning("Đây là vị trí của thiết bị đang mở website, không tự động là vị trí xe container. Muốn theo dõi xe thật, tài xế phải mở trang này trên điện thoại mang theo xe hoặc hệ thống phải nhận dữ liệu từ thiết bị GPS của nhà xe. Không dùng khi chưa được người cầm thiết bị đồng ý.")

    gps_col, route_col = st.columns([1, 1])
    with gps_col:
        st.markdown("#### 1. Lấy vị trí hiện tại")
        try:
            location = streamlit_geolocation()
        except Exception as e:
            location = None
            st.error(f"Không tải được thành phần GPS: {e}")

        if isinstance(location, dict) and location.get("latitude") is not None and location.get("longitude") is not None:
            gps_lat = float(location["latitude"])
            gps_lon = float(location["longitude"])
            gps_accuracy = location.get("accuracy")
            st.success("Đã nhận tọa độ từ trình duyệt.")
            g1, g2 = st.columns(2)
            g1.metric("Vĩ độ", f"{gps_lat:.6f}")
            g2.metric("Kinh độ", f"{gps_lon:.6f}")
            if gps_accuracy is not None:
                st.caption(f"Độ chính xác trình duyệt báo: khoảng {float(gps_accuracy):.0f} m. Độ chính xác thực tế phụ thuộc thiết bị và môi trường.")
            st.session_state["gps_lat"] = gps_lat
            st.session_state["gps_lon"] = gps_lon
            st.session_state["gps_accuracy"] = gps_accuracy
        else:
            st.info("Bấm nút định vị trong khung bên dưới và chọn Allow/Cho phép khi trình duyệt hỏi quyền vị trí.")
            gps_lat = st.session_state.get("gps_lat")
            gps_lon = st.session_state.get("gps_lon")

    with route_col:
        st.markdown("#### 2. Tính tuyến đường đến cảng")
        st.caption(f"Điểm đến hiện chọn: {port_name}. Tọa độ cảng là tọa độ khu vực tham khảo, không bảo đảm trùng cổng terminal.")
        if st.button("Tính tuyến đường từ GPS đến cảng", type="primary", use_container_width=True):
            gps_lat = st.session_state.get("gps_lat")
            gps_lon = st.session_state.get("gps_lon")
            if gps_lat is None or gps_lon is None:
                st.error("Chưa có tọa độ GPS. Lấy vị trí trước rồi bấm tính tuyến đường.")
            else:
                try:
                    route_url = f"https://router.project-osrm.org/route/v1/driving/{gps_lon},{gps_lat};{port_lon},{port_lat}"
                    route_response = requests.get(route_url, params={"overview": "full", "geometries": "geojson", "steps": "false"}, timeout=20)
                    route_response.raise_for_status()
                    route_json = route_response.json()
                    if route_json.get("code") != "Ok" or not route_json.get("routes"):
                        st.error("Không tìm được tuyến đường. Kiểm tra tọa độ hoặc thử lại sau.")
                    else:
                        route = route_json["routes"][0]
                        st.session_state["osrm_route"] = route
                        st.session_state["osrm_origin"] = [gps_lat, gps_lon]
                        st.session_state["osrm_destination"] = [port_lat, port_lon]
                        st.session_state["osrm_route_error"] = None
                except Exception as e:
                    st.session_state["osrm_route_error"] = str(e)
                    st.error("Không kết nối được dịch vụ định tuyến miễn phí lúc này. Có thể thử lại sau.")

    if st.session_state.get("osrm_route") and st.session_state.get("osrm_origin"):
        route = st.session_state["osrm_route"]
        distance_km = route["distance"] / 1000
        drive_hours = route["duration"] / 3600
        r1, r2, r3 = st.columns(3)
        r1.metric("Khoảng cách tuyến tham khảo", f"{distance_km:.1f} km")
        r2.metric("Thời gian lái xe ước tính", f"{drive_hours:.1f} giờ")
        r3.metric("Nguồn", "OSRM / OpenStreetMap")
        st.caption("Thời gian OSRM là ước tính theo mạng đường, không phải dữ liệu giao thông trực tiếp. Chưa bao gồm thời gian nghỉ, kiểm tra, chờ cổng, hạn chế xe tải hoặc điều kiện vận hành thực tế.")
        route_map = folium.Map(location=st.session_state["osrm_origin"], zoom_start=8, control_scale=True)
        folium.Marker(st.session_state["osrm_origin"], tooltip="Vị trí GPS thiết bị", popup="Vị trí GPS thiết bị", icon=folium.Icon(color="blue", icon="info-sign")).add_to(route_map)
        folium.Marker(st.session_state["osrm_destination"], tooltip=port_name, popup=port_name, icon=folium.Icon(color="red", icon="flag")).add_to(route_map)
        coords = route.get("geometry", {}).get("coordinates", [])
        if coords:
            folium.PolyLine([(lat, lon) for lon, lat in coords], tooltip="Tuyến đường tham khảo", weight=5).add_to(route_map)
        st_folium(route_map, use_container_width=True, height=450, returned_objects=[])

        st.markdown("#### 3. Thời tiết tại vị trí GPS hiện tại")
        try:
            live_weather = get_weather(st.session_state["gps_lat"], st.session_state["gps_lon"])
            live_summary = weather_summary(live_weather)
            w1, w2, w3, w4 = st.columns(4)
            w1.metric("Thời tiết", live_summary["description"])
            w2.metric("Nhiệt độ", f"{live_summary['temperature']} °C" if live_summary["temperature"] is not None else "N/A")
            w3.metric("Mưa", f"{live_summary['rain']:.1f} mm")
            w4.metric("Gió", f"{live_summary['wind']:.0f} km/h")
            if live_summary["reasons"]:
                st.warning("Tín hiệu thời tiết cần lưu ý: " + "; ".join(live_summary["reasons"]))
        except Exception as e:
            st.info("Chưa lấy được thời tiết tại vị trí GPS. Kiểm tra kết nối mạng hoặc thử lại.")
    else:
        st.info("Sau khi lấy GPS và tính tuyến đường thành công, bản đồ, khoảng cách, ETA tham khảo và thời tiết tại vị trí thiết bị sẽ xuất hiện ở đây.")

with tab3:
    st.subheader("Minh bạch về dữ liệu và giới hạn")
    st.markdown("""
- **Thời tiết:** lấy qua Open-Meteo API, không yêu cầu API key. Dữ liệu trong bản demo là thời tiết tại tọa độ khu vực cảng, không đại diện toàn bộ tuyến đường.
- **Giao thông:** mức độ giao thông hiện đang là trường nhập tay. Chưa kết nối nguồn ùn tắc trực tiếp, nên không được hiểu là dữ liệu giao thông thời gian thực.
- **GPS:** chưa theo dõi xe trực tiếp. Muốn có GPS thật cần dữ liệu từ thiết bị/nhà vận tải có quyền truy cập.
- **Lịch tàu và cut-off:** cần lấy từ booking/thông báo của hãng tàu hoặc đại lý và cập nhật khi có thay đổi.
- **Dự báo rủi ro:** điểm 0–100 hiện là bộ quy tắc minh họa, **không phải xác suất thống kê và chưa phải mô hình ML đã huấn luyện**. Cần dùng dữ liệu lịch sử, định nghĩa rõ nhãn kết quả và đánh giá trên tập kiểm thử trước khi công bố độ chính xác.
- **Quyết định vận hành:** các phương án chỉ là gợi ý. Nhân viên cần xác minh với điều độ, cảng, hãng tàu và khách hàng trước khi thực hiện.
""")
    st.markdown("Nguồn thời tiết: [Open-Meteo API](https://open-meteo.com/en/docs). Dùng dịch vụ miễn phí theo điều khoản hiện hành của nhà cung cấp.")

st.markdown("---")
st.caption("Prototype VYLT 2026 • Không dùng để ra quyết định vận hành thực tế nếu chưa xác minh dữ liệu, ngưỡng và quy trình với doanh nghiệp.")
