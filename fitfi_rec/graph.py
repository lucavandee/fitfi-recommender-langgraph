"""Wire nodes into a compiled LangGraph StateGraph."""

from langgraph.graph import StateGraph, START, END
from .state import State
from .nodes import (
    derive_archetype,
    filter_products,
    reclassify,
    photo_enhance,
    assemble,
    rank,
    diversity,
    needs_photo_enhance,
)


def build_graph():
    """Return a compiled LangGraph app.

    Flow:
        START -> archetype -> filter -> reclassify
                 -> (color_profile? -> photo_enhance) -> assemble
                 -> rank -> diversity -> END
    """
    g = StateGraph(State)

    g.add_node("archetype", derive_archetype)
    g.add_node("filter", filter_products)
    g.add_node("reclassify", reclassify)
    g.add_node("photo_enhance", photo_enhance)
    g.add_node("assemble", assemble)
    g.add_node("rank", rank)
    g.add_node("diversity", diversity)

    g.add_edge(START, "archetype")
    g.add_edge("archetype", "filter")
    g.add_edge("filter", "reclassify")
    g.add_conditional_edges(
        "reclassify",
        needs_photo_enhance,
        {"photo_enhance": "photo_enhance", "assemble": "assemble"},
    )
    g.add_edge("photo_enhance", "assemble")
    g.add_edge("assemble", "rank")
    g.add_edge("rank", "diversity")
    g.add_edge("diversity", END)

    return g.compile()
