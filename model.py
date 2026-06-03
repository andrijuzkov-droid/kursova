from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple
import random

import networkx as nx
import pandas as pd

State = str

@dataclass
class SimulationResult:
 timeline: pd.DataFrame
 node_states: pd.DataFrame
 risk_scores: pd.DataFrame

class AttackSpreadSimulator:
 """Stochastic SI/SIS/SIR simulator on an undirected network graph."""

 def __init__(self, graph: nx.Graph, seed: Optional[int] = None) -> None:
  if graph.number_of_nodes() == 0:
   raise ValueError("Graph must contain at least one node.")
  self.graph = graph.copy()
  self.random = random.Random(seed)

 def run(
  self,
  model: str,
  initial_infected: Iterable[str],
  steps: int,
  beta: float,
  gamma: float = 0.0,
  reinfection_rate: float = 0.0,
 ) -> SimulationResult:
  model = model.upper().strip()
  if model not in {"SI", "SIS", "SIR"}:
   raise ValueError("model must be one of: SI, SIS, SIR")
  if steps < 1:
   raise ValueError("steps must be >= 1")
  if not (0 <= beta <= 1):
   raise ValueError("beta must be in [0,1]")
  if not (0 <= gamma <= 1):
   raise ValueError("gamma must be in [0,1]")
  if not (0 <= reinfection_rate <= 1):
   raise ValueError("reinfection_rate must be in [0,1]")

  nodes = [str(n) for n in self.graph.nodes()]
  states: Dict[str, State] = {node: "S" for node in nodes}

  infected_set = {str(n) for n in initial_infected if str(n) in states}
  if not infected_set:
   # fallback: infect one random node so simulation is meaningful
   infected_set = {self.random.choice(nodes)}
  for node in infected_set:
   states[node] = "I"

  timeline_rows: List[Dict[str, float]] = []
  state_rows: List[Dict[str, str]] = []

  for step in range(steps + 1):
   counts = self._count_states(states)
   timeline_rows.append(
 {
  "step": step,
  "susceptible": counts.get("S", 0),
  "infected": counts.get("I", 0),
  "recovered": counts.get("R", 0),
 }
   )
   state_rows.append({"step": step, **states})

   if step == steps:
 break

   next_states = states.copy()

   # infection phase
   for node in nodes:
 node_state = states[node]
 if node_state == "I":
  continue
 if node_state == "R" and model == "SIR":
  continue

 infected_neighbors = sum(
  1 for neigh in self.graph.neighbors(node) if states[str(neigh)] == "I"
 )
 if infected_neighbors == 0:
  continue

 # Independent trial per infected neighbor.
 # For reinfection in SIS use separate lower probability if configured.
 p = beta
 if node_state == "R" and model == "SIS":
  p = reinfection_rate if reinfection_rate > 0 else beta

 infection_probability = 1.0 - ((1.0 - p) ** infected_neighbors)
 if self.random.random() < infection_probability:
  next_states[node] = "I"

   # recovery phase
   if model in {"SIS", "SIR"} and gamma > 0:
 for node in nodes:
  if states[node] != "I":
   continue
  if self.random.random() < gamma:
   next_states[node] = "S" if model == "SIS" else "R"

   states = next_states

  timeline_df = pd.DataFrame(timeline_rows)
  states_df = pd.DataFrame(state_rows)
  risk_df = self._build_risk_scores(states_df)

  return SimulationResult(timeline=timeline_df, node_states=states_df, risk_scores=risk_df)

 def _count_states(self, states: Dict[str, State]) -> Dict[State, int]:
  result: Dict[State, int] = {}
  for value in states.values():
   result[value] = result.get(value, 0) + 1
  return result

 def _build_risk_scores(self, states_df: pd.DataFrame) -> pd.DataFrame:
  node_cols = [c for c in states_df.columns if c != "step"]
  total_steps = len(states_df)
  rows = []
  for node in node_cols:
   infected_steps = int((states_df[node] == "I").sum())
   first_infection_series = states_df.index[states_df[node] == "I"]
   first_infection_step = int(first_infection_series.min()) if len(first_infection_series) else -1
   rows.append(
 {
  "node": node,
  "infected_steps": infected_steps,
  "infection_ratio": infected_steps / total_steps,
  "first_infection_step": first_infection_step,
  "degree": int(self.graph.degree[node]) if node in self.graph else 0,
  "betweenness": 0.0,
  "risk_score": 0.0,
 }
   )

  risk = pd.DataFrame(rows)
  if risk.empty:
   return risk

  betweenness = nx.betweenness_centrality(self.graph)
  risk["betweenness"] = risk["node"].map(lambda n: float(betweenness.get(n, 0.0)))

  deg_max = max(risk["degree"].max(), 1)
  risk["degree_norm"] = risk["degree"] / deg_max

  # Weighted composite metric
  risk["risk_score"] = (
   0.5 * risk["infection_ratio"]
   + 0.3 * risk["degree_norm"]
   + 0.2 * risk["betweenness"]
  )

  risk = risk.sort_values("risk_score", ascending=False).reset_index(drop=True)
  return risk[[
   "node",
   "infected_steps",
   "infection_ratio",
   "first_infection_step",
   "degree",
   "betweenness",
   "risk_score",
  ]]

def graph_from_edges(edge_df: pd.DataFrame) -> nx.Graph:
 required = {"source", "target"}
 if not required.issubset(set(edge_df.columns)):
  raise ValueError("Edge table must contain columns: source, target")

 clean = edge_df.copy()
 clean["source"] = clean["source"].astype(str).str.strip()
 clean["target"] = clean["target"].astype(str).str.strip()
 clean = clean[(clean["source"] != "") & (clean["target"] != "")]

 if clean.empty:
  raise ValueError("Edge table is empty after cleanup.")

 g = nx.from_pandas_edgelist(clean, source="source", target="target")
 if g.number_of_nodes() == 0:
  raise ValueError("No valid nodes in graph.")
 return g

def default_graph() -> nx.Graph:
 # Small but expressive topology for demonstration.
 edges: List[Tuple[str, str]] = [
  ("Gateway", "DMZ"),
  ("Gateway", "Admin-PC"),
  ("DMZ", "Web-Server"),
  ("DMZ", "Mail-Server"),
  ("Web-Server", "DB-Server"),
  ("Mail-Server", "DB-Server"),
  ("DB-Server", "Backup"),
  ("Admin-PC", "HR-PC"),
  ("Admin-PC", "Dev-PC"),
  ("Dev-PC", "CI-Server"),
  ("CI-Server", "Repo"),
  ("Repo", "DB-Server"),
  ("HR-PC", "File-Server"),
  ("File-Server", "Backup"),
 ]
 g = nx.Graph()
 g.add_edges_from(edges)
 return g

