import reflex as rx

config = rx.Config(
    app_name="reflex_demo", frontend_port=3001, backend_port=3001,
    api_url="http://127.0.0.1:3001", backend_host="127.0.0.1",
)
