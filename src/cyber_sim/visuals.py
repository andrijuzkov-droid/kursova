```python
from __future__ import annotations

from typing import Dict, List

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

STATE_COLORS = {
 "S": "#9ca3af",  # gray
 "I": "#ef4444",  # red
 "R": "#10b981",  # green
}

def timeline_figure(timeline: pd.DataFrame) -> go.Figure:
 long_df = timeline.melt(
  id_vars=["step"],
  value_vars=["susceptible", "infected", "recovered"],
  var_name="state",
  value_name="count",
 )
 name_map = {
  "susceptible": "Susceptible",
  "infected": "Infected",
  "recovered": "Recovered",
 }
 long_df["state"] = long_df["state"].map(name_map)

 fig = px.line(
  long_df,
  x="step",
  y="count",
  color="state",
  markers=True,
  color_discrete_map={
   "Susceptible": STATE_COLORS["S"],
   "Infected": STATE_COLORS["I"],
   "Recovered": STATE_COLORS["R"],
  },
  title="Attack Spread Dynamics by Step",
 )
 fig.update_layout(template="plotly_white", legend_title_text="Node state")
 return fig

def risk_bar_figure(risk_scores: pd.DataFrame, top_n: int = 10) -> go.Figure:
 top = risk_scores.head(top_n).copy()
 fig = px.bar(
  top,
  x="node",
  y="risk_score",
  title=f"Top {min(top_n, len(top))} High-Risk Nodes",
  labels={"node": "Node", "risk_score": "Risk score"},
  color="risk_score",
  color_continuous_scale="OrRd",
 )
 fig.update_layout(template="plotly_white", coloraxis_showscale=False)
 return fig

def network_state_figure(
 graph: nx.Graph,
 node_states_at_step: Dict[str, str],
 highlight_risk: Dict[str, float] | None = None,
) -> go.Figure:
 pos = nx.spring_layout(graph, seed=42)

 edge_x: List[float] = []
 edge_y: List[float] = []
 for source, target in graph.edges():
  x0, y0 = pos[source]
  x1, y1 = pos[target]
  edge_x.extend([x0, x1, None])
  edge_y.extend([y0, y1, None])

 edge_trace = go.Scatter(
  x=edge_x,
  y=edge_y,
  line=dict(width=1.0, color="#9ca3af"),
  hoverinfo="none",
  mode="lines",
  name="links",
 )

 node_x: List[float] = []
 node_y: List[float] = []
 node_text: List[str] = []
 node_color: List[str] = []
 node_size: List[float] = []

 for node in graph.nodes():
  x, y = pos[node]
  state = node_states_at_step.get(str(node), "S")
  risk = (highlight_risk or {}).get(str(node), 0.0)

  node_x.append(x)
  node_y.append(y)
  node_color.append(STATE_COLORS.get(state, STATE_COLORS["S"]))
  node_size.append(16 + 26 * risk)
  node_text.append(f"{node}<br>State: {state}<br>Risk: {risk:.3f}")

 node_trace = go.Scatter(
  x=node_x,
  y=node_y,
  mode="markers+text",
  text=[str(n) for n in graph.nodes()],
  textposition="top center",
  hoverinfo="text",
  hovertext=node_text,
  marker=dict(
   color=node_color,
   size=node_size,
   line=dict(width=1.3, color="#1f2937"),
  ),
  name="nodes",
 )

 fig = go.Figure(data=[edge_trace, node_trace])
 fig.update_layout(
  title="Network State",
  template="plotly_white",
  showlegend=False,
  margin=dict(l=10, r=10, t=45, b=10),
  xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
  yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
 )
 return fig
```
