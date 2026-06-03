from __future__ import annotations

from io import BytesIO
import os
import sys
import traceback

import pandas as pd
import streamlit as st

# ==============================================================================
# 1) АВТОМАТИЧНЕ НАЛАШТУВАННЯ ШЛЯХІВ ТА БЕЗПЕЧНИЙ ІМПОРТ
# ==============================================================================
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
parent_dir = os.path.dirname(current_dir)

# Додаємо робочі директорії до системного шляху Python
for path in [current_dir, parent_dir]:
    if path not in sys.path:
        sys.path.append(path)

src_path = os.path.join(current_dir, "src")
if os.path.exists(src_path) and src_path not in sys.path:
    sys.path.append(src_path)

# Спроба імпортувати модулі з відловлюванням SyntaxError або ModuleNotFoundError
try:
    from src.cyber_sim import AttackSpreadSimulator, default_graph, graph_from_edges
    from src.cyber_sim.io_utils import parse_uploaded_csv
    from src.cyber_sim.visuals import network_state_figure, risk_bar_figure, timeline_figure
except Exception as e:
    st.error("🚨 Помилка ініціалізації модулів додатка!")
    st.write("Streamlit Cloud не зміг завантажити файли симулятора через внутрішню помилку в коді:")
    st.code(traceback.format_exc())
    st.stop()

# ==============================================================================
# 2) КОНФІГУРАЦІЯ СТОРІНКИ ТА ІНТЕРФЕЙСУ
# ==============================================================================
st.set_page_config(
    page_title="Cyber Attack Spread Simulator",
    page_icon="🛡️",
    layout="wide",
)

st.title("Інтерактивне моделювання поширення кібератаки у мережі")
st.caption("Навчальний веб-застосунок на базі Streamlit для SI/SIS/SIR-моделювання")

with st.sidebar:
    st.header("Параметри模делі")
    model_name = st.selectbox("Модель", ["SI", "SIS", "SIR"], index=2)
    steps = st.slider("Кількість кроків симуляції", min_value=5, max_value=120, value=40)
    beta = st.slider("Ймовірність зараження β", min_value=0.0, max_value=1.0, value=0.35, step=0.01)

    gamma = 0.0
    reinfection_rate = 0.0
    if model_name in {"SIS", "SIR"}:
        gamma = st.slider("Ймовірність відновлення γ", min_value=0.0, max_value=1.0, value=0.12, step=0.01)
    if model_name == "SIS":
        reinfection_rate = st.slider("Ймовірність повторного зараження", min_value=0.0, max_value=1.0, value=0.20, step=0.01)

    seed = st.number_input("Random seed", min_value=0, max_value=999999, value=42)

st.subheader("1) Завантаження або генерація топології")
source_tab, template_tab = st.tabs(["Завантажити CSV", "Типова топологія"])

loaded_graph = None
edges_df = None

with source_tab:
    st.write("CSV повинен містити колонки: `source,target`.")
    uploaded = st.file_uploader("Оберіть файл з ребрами графа", type=["csv"])
    if uploaded is not None:
        try:
            uploaded_df = parse_uploaded_csv(uploaded.read())
            loaded_graph = graph_from_edges(uploaded_df)
            edges_df = uploaded_df
            st.success(f"Топологію завантажено: вузлів {loaded_graph.number_of_nodes()}, зв'язків {loaded_graph.number_of_edges()}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Не вдалося обробити файл: {exc}")

with template_tab:
    if st.button("Використати типову топологію", use_container_width=True):
        loaded_graph = default_graph()
        edges_df = pd.DataFrame(list(loaded_graph.edges()), columns=["source", "target"])
        st.success("Типову топологію підготовлено.")

if loaded_graph is None:
    loaded_graph = default_graph()
    edges_df = pd.DataFrame(list(loaded_graph.edges()), columns=["source", "target"])

all_nodes = [str(n) for n in loaded_graph.nodes()]
default_initial = all_nodes[:1] if all_nodes else []

st.subheader("2) Початкові умови атаки")
initial_infected = st.multiselect(
    "Оберіть початково скомпрометовані вузли",
    options=all_nodes,
    default=default_initial,
)

if not initial_infected:
    st.info("Не обрано жодного вузла. Під час запуску буде автоматично обрано один випадковий вузол.")

run_clicked = st.button("Запустити симуляцію", type="primary", use_container_width=True)

# ==============================================================================
# 3) ЗАПУСК СИМУЛЯЦІЇ ТА ВІЗУАЛІЗАЦІЯ
# ==============================================================================
if run_clicked:
    try:
        simulator = AttackSpreadSimulator(loaded_graph, seed=int(seed))
        result = simulator.run(
            model=model_name,
            initial_infected=initial_infected,
            steps=int(steps),
            beta=float(beta),
            gamma=float(gamma),
            reinfection_rate=float(reinfection_rate),
        )

        st.success("Симуляцію виконано успішно.")

        c1, c2, c3 = st.columns(3)
        final = result.timeline.iloc[-1]
        c1.metric("Infected (final)", int(final["infected"]))
        c2.metric("Susceptible (final)", int(final["susceptible"]))
        c3.metric("Recovered (final)", int(final["recovered"]))

        left, right = st.columns([1.7, 1.3])
        with left:
            st.plotly_chart(timeline_figure(result.timeline), use_container_width=True)
        with right:
            st.plotly_chart(risk_bar_figure(result.risk_scores, top_n=10), use_container_width=True)

        st.subheader("3) Інтерактивний перегляд стану мережі")
        view_step = st.slider(
            "Крок для перегляду стану вузлів",
            min_value=0,
            max_value=int(result.timeline["step"].max()),
            value=int(result.timeline["step"].max()),
        )

        step_row = result.node_states[result.node_states["step"] == view_step]
        step_states = {}
        if not step_row.empty:
            row = step_row.iloc[0].to_dict()
            step_states = {k: v for k, v in row.items() if k != "step"}

        risk_map = {
            r["node"]: float(r["risk_score"])
            for _, r in result.risk_scores.iterrows()
        }
        st.plotly_chart(
            network_state_figure(loaded_graph, step_states, highlight_risk=risk_map),
            use_container_width=True,
        )

        st.subheader("4) Таблиці результатів")
        t1, t2, t3 = st.tabs(["Динаміка", "Стани вузлів", "Ризики вузлів"])
        with t1:
            st.dataframe(result.timeline, use_container_width=True)
        with t2:
            st.dataframe(result.node_states, use_container_width=True)
        with t3:
            st.dataframe(result.risk_scores, use_container_width=True)

        st.subheader("5) Експорт результатів")
        out_timeline = result.timeline.to_csv(index=False).encode("utf-8")
        out_states = result.node_states.to_csv(index=False).encode("utf-8")
        out_risks = result.risk_scores.to_csv(index=False).encode("utf-8")
        out_edges = edges_df.to_csv(index=False).encode("utf-8") if edges_df is not None else b""

        d1, d2, d3, d4 = st.columns(4)
        d1.download_button("timeline.csv", out_timeline, file_name="timeline.csv", mime="text/csv", use_container_width=True)
        d2.download_button("node_states.csv", out_states, file_name="node_states.csv", mime="text/csv", use_container_width=True)
        d3.download_button("risk_scores.csv", out_risks, file_name="risk_scores.csv", mime="text/csv", use_container_width=True)
        d4.download_button("edges.csv", out_edges, file_name="edges.csv", mime="text/csv", use_container_width=True)

    except Exception as exc:  # noqa: BLE001
        st.error(f"Помилка під час симуляції: {exc}")

st.markdown("---")
st.caption(
    "Модель призначена для навчального і дослідницького моделювання. "
    "Не використовує реальні службові дані та не виконує мережевих атак."
)
