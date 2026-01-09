import os
import torch
import ollama
from diffusers import StableDiffusionPipeline

from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama


class get_result:
    def __init__(self):
        # Ollama LAN client (optional direct use)
        self.client = ollama.Client(host="http://172.18.1.152:11434")

        # ✅ Single LLM for EVERYTHING (QA + summarization)
        self.llm = ChatOllama(
            model="llama3.1",
            temperature=0.3,  # lower = better academic summarization
            base_url="http://172.18.1.152:11434"
        )

    # ==========================================================
    # MAIN QA / RAG RESPONSE
    # ==========================================================
    def extract_result(self, text, query, recent_history, references_for_each_chunk):

        prompt_extract = PromptTemplate.from_template(
            """
            ### Chat History:
            {recent_history}

            ### User Question:
            {query}

            ### Retrieved Text Chunks:
            {text_chunks}

            ### Corresponding References:
            {references_for_each_chunk}

            ### Instructions:
            You are an academic research assistant specializing in disaster management.

            Strict rules:
            - Cite only valid references (no placeholders)
            - IEEE in-text citations [1], [2]
            - No references section if none are valid
            - Academic tone, no AI mentions
            - If unrelated to disaster management:
              "I can't answer, please ask questions relevant to disaster management."

            ### NO PREAMBLE
            ### Response:
            """
        )

        chain = prompt_extract | self.llm

        result = chain.invoke({
            "text_chunks": text,
            "query": query,
            "recent_history": recent_history,
            "references_for_each_chunk": references_for_each_chunk
        })

        return result.content

    # ==========================================================
    # STABLE DIFFUSION IMAGE GENERATION
    # ==========================================================
    def call_stable_diffusion(self, summary):
        model_id = "runwayml/stable-diffusion-v1-5"

        pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float32
        )
        pipe = pipe.to("cpu")

        image = pipe(summary).images[0]
        image.save("generated_image.png")

        return image

    # ==========================================================
    # SHORT ACADEMIC SUMMARY (LLaMA)
    # ==========================================================
    def llama_summarize(self, text, max_words=120):
        prompt = PromptTemplate.from_template(
            """
            You are an academic disaster management expert.

            Summarize the following text:
            - Preserve technical accuracy
            - Keep cause–effect relationships
            - Maximum {max_words} words
            - No preamble

            ### Text:
            {text}

            ### Summary:
            """
        )

        chain = prompt | self.llm
        result = chain.invoke({"text": text, "max_words": max_words})
        return result.content

    # ==========================================================
    # LONG TEXT SUMMARY (MAP–REDUCE STYLE)
    # ==========================================================
    def extract_result_4(self, text, chunk_size=1400):

        def chunk_text(text, size):
            words = text.split()
            return [
                " ".join(words[i:i + size])
                for i in range(0, len(words), size)
            ]

        chunks = chunk_text(text, chunk_size)

        partial_summaries = []
        for chunk in chunks:
            summary = self.llama_summarize(chunk, max_words=120)
            partial_summaries.append(summary)

        final_prompt = PromptTemplate.from_template(
            """
            Combine the following summaries into one coherent academic summary.
            Remove redundancy and improve logical flow.

            ### Summaries:
            {summaries}

            ### Final Summary:
            """
        )

        chain = final_prompt | self.llm
        result = chain.invoke({"summaries": "\n".join(partial_summaries)})

        return result.content
