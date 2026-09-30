from mcp.server import MCPServer

from rag_pipeline import answer_question as answer_question_impl
from rag_pipeline import refresh_corpus as refresh_corpus_impl
from rag_pipeline import retrieve_context as retrieve_context_impl


mcp = MCPServer(
	"Student 2 Staff RAG",
	instructions="Answer staff questions only from retrieved staff registry evidence and include citations.",
)


@mcp.tool()
def refresh_corpus(caller: str = "student") -> dict:
	"""Refresh the local vector index from the staff registry."""
	return refresh_corpus_impl(caller=caller)


@mcp.tool()
def retrieve_context(query: str, k: int = 5, caller: str = "student") -> dict:
	"""Retrieve staff registry chunks relevant to a query."""
	return retrieve_context_impl(query=query, k=k, caller=caller)


@mcp.tool()
def answer_question(query: str, k: int = 5, caller: str = "student") -> dict:
	"""Answer from retrieved staff evidence with citations and confidence."""
	return answer_question_impl(query=query, k=k, caller=caller)


if __name__ == "__main__":
	mcp.run()