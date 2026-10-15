# Báo cáo Lab Day 26 — MCP và Function Calling

Sinh viên: **Dương Thị Ngân**  
MSSV: **2A202602808**  
Ngày thực hiện: **14–15/10/2026**

## Kết quả

| Phần | Trạng thái | Minh chứng |
|---|---|---|
| Function Calling với Gemini | Đạt — model gọi tool cho Hà Nội và Đà Nẵng, app thực thi rồi model tổng hợp | [Ảnh](screenshots/01-function-calling.png) |
| MCP server/client qua `stdio` | Đạt — client khám phá và gọi `get_weather` cho 3 thành phố | [Ảnh](screenshots/02-mcp-client.png) |
| Bearer-token authentication | Đạt — token đúng được phép, token sai bị từ chối | [Token đúng](screenshots/03a-auth-ok.png) · [Token sai](screenshots/03a-auth-fail.png) |
| Tool Registry | Đạt — tìm 2 weather tools và chọn bản v2 không deprecated | [Ảnh](screenshots/03b-registry.png) |
| Versioning | Đạt — v1 tương thích ngược, v2 trả JSON và forecast | [Ảnh](screenshots/03c-versioning.png) |
| MCP server qua Streamable HTTP | Đạt — khám phá đủ 3 tools, lấy thời tiết hiện tại và dự báo thật | [Ảnh](screenshots/04-mcp-http-server.png) |
| Google ADK setup | Đạt — dependencies, cấu trúc agent, MCP endpoint và import đều hợp lệ | [Ảnh](screenshots/04-verify-setup.png) |
| ADK chat dùng dữ liệu thời tiết thật | Đạt — agent tự gọi MCP tool cho thời tiết hiện tại và dự báo 3 ngày | [Hiện tại](screenshots/04-adk-current.png) · [Dự báo](screenshots/04-adk-forecast.png) |

## Các lỗi tương thích đã sửa

1. `registry_client.py` mở `registry.json` bằng UTF-8 để chạy đúng trên Windows.
2. Model `gemini-2.5-flash` đã bị ngừng phục vụ cho user mới, nên model được cấu hình bằng biến `GEMINI_MODEL`, mặc định là `gemini-3.8-flash`.
3. Thay SDK cũ `google-generativeai` đã hết hỗ trợ bằng `google-genai`.
4. `verify_setup.py` không còn in một phần API key ra terminal/screenshot.
5. Demo auth xử lý lỗi token sai gọn gàng và tắt cảnh báo audience validation đúng với static-token demo.
6. WeatherAPI vẫn là nguồn chính khi có `WEATHERAPI_KEY`; nếu chưa có key, server tự dùng Open-Meteo để bài lab vẫn chạy với dữ liệu thời tiết thật.

## Lệnh chạy lại

```powershell
# Terminal 1
cd 04-lab/mcp-server
# Không bắt buộc: nếu có key, server ưu tiên WeatherAPI.
$env:WEATHERAPI_KEY="<weatherapi-key>"
uv sync
uv run python weather.py

# Terminal 2
cd 04-lab/mcp-client
# Tạo .env UTF-8: GOOGLE_API_KEY=<gemini-key>
uv sync
uv run python verify_setup.py
uv run adk web
```

Nếu không đặt `WEATHERAPI_KEY`, server tự chuyển sang Open-Meteo. Mở
`http://localhost:8000` để hỏi thời tiết hiện tại hoặc dự báo 1–3 ngày.

## Kiến thức rút ra

- **Function Calling** là khả năng model chọn function và sinh arguments; app vẫn là nơi thực thi function.
- **MCP** chuẩn hóa cách client khám phá và gọi tools từ server độc lập.
- **Google ADK** tự thực hiện vòng lặp: nhận câu hỏi → model chọn tool → gọi MCP → đưa kết quả về model → tạo câu trả lời.
- Khi đưa MCP lên production cần thêm authentication, registry/discovery, versioning, health check và logging.
