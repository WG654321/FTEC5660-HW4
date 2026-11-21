"""Run one cumulative variant using the unchanged course evaluator."""
import sys

from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi

import hw4


def configure(variant):
    if variant in ("B0", "V1"):
        splitter = RecursiveCharacterTextSplitter(chunk_size=1100, chunk_overlap=100)

        def split(source, html):
            soup = BeautifulSoup(html, "lxml")
            meta = hw4.metadata(source, soup)
            if variant == "V1":
                for table in soup.find_all("table"):
                    table.replace_with(hw4.table_to_text(str(table)))
            return splitter.create_documents([soup.get_text(" ", strip=True)], metadatas=[meta])

        hw4.chunk_document = split
    if variant == "B0":
        hw4.table_to_text = lambda html: BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    if variant in ("B0", "V1", "V2"):
        def build(chunks):
            return chunks, BM25Okapi([c.page_content.lower().split() for c in chunks])

        def retrieve(index, question):
            chunks, bm25 = index
            return bm25.get_top_n(question.lower().split(), chunks, n=5)

        hw4.build_index = build
        hw4.retrieve = retrieve
        hw4.parse_query = lambda question: {}
    if variant == "V2S":
        def build_scoped(chunks):
            groups = {}
            for i, chunk in enumerate(chunks):
                meta = chunk.metadata
                groups.setdefault((hw4.company_key(meta["company"]), meta["doc_type"]), []).append(i)
            return chunks, BM25Okapi([c.page_content.lower().split() for c in chunks]), groups

        def retrieve_scoped(index, question):
            chunks, model, groups = index
            scores = model.get_scores(question.lower().split())
            return hw4.scoped_top(chunks, groups, hw4.parse_query(question), scores.__getitem__)

        hw4.build_index = build_scoped
        hw4.retrieve = retrieve_scoped
    if variant == "V3":
        hw4.retrieve = lambda index, q: hw4.ranked(index, q, hw4.parse_query(q))


if __name__ == "__main__":
    variant = sys.argv.pop(1)
    if variant not in ("B0", "V1", "V2", "V2S", "V3", "V4"):
        raise SystemExit("Choose B0, V1, V2, V2S, V3 or V4")
    configure(variant)
    hw4.main()
