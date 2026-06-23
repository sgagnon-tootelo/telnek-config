import pandas as pd
import plotly.express as px

from ui.theme import BRAND_PRIMARY, apply_brand_plotly, brand_color_sequence


def test_brand_color_sequence_wraps_palette() -> None:
    colors = brand_color_sequence(5)
    assert len(colors) == 5
    assert colors[0] == BRAND_PRIMARY
    assert colors[1] != colors[0]


def test_apply_brand_plotly_sets_transparent_background() -> None:
    plotly = __import__("plotly.graph_objects", fromlist=["go"])
    fig = plotly.Figure(data=[plotly.Bar(x=["a"], y=[1])])
    styled = apply_brand_plotly(fig)
    assert styled.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert styled.layout.plot_bgcolor == "rgba(0,0,0,0)"


def test_apply_brand_plotly_pie_chart_does_not_raise() -> None:
    df = pd.DataFrame({"Type": ["A", "B", "C"], "Nombre": [1, 2, 3]})
    fig = px.pie(
        df,
        values="Nombre",
        names="Type",
        color_discrete_sequence=brand_color_sequence(3),
    )
    apply_brand_plotly(fig)