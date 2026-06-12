import re


def semantic_chunk_text(text: str, target_size: int = 600, min_size: int = 100, overlap_sentences: int = 2) -> list[str]:
    """Split text into semantically coherent chunks.

    Respects sentence and paragraph boundaries.
    Produces chunks of approximately target_size characters.
    Includes overlap_sentences sentences from the end of the previous chunk for context.
    """
    if not text or not text.strip():
        return []

    # Split into sentences, respecting paragraph boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks = []
    current_chunk_sentences: list[str] = []
    current_size = 0
    # Store sentences from the end of previous chunk for overlap
    prev_sentences: list[str] = []

    for sentence in sentences:
        sentence_len = len(sentence)

        # If adding this sentence would exceed target_size and we already have content, flush
        if current_chunk_sentences and current_size + sentence_len + 1 > target_size:
            # Build chunk text
            chunk_text = " ".join(current_chunk_sentences)
            if len(chunk_text) >= min_size or not chunks:
                chunks.append(chunk_text)
                # Keep last N sentences for overlap
                prev_sentences = current_chunk_sentences[-overlap_sentences:] if overlap_sentences > 0 else []
            else:
                # Too small — merge with previous chunk
                if chunks:
                    chunks[-1] = chunks[-1] + " " + chunk_text
                else:
                    chunks.append(chunk_text)
                prev_sentences = []

            # Start new chunk with overlap sentences
            current_chunk_sentences = list(prev_sentences)
            current_size = sum(len(s) + 1 for s in current_chunk_sentences) if current_chunk_sentences else 0

        # Check if this single sentence is longer than target_size
        if not current_chunk_sentences and sentence_len > target_size:
            # Very long sentence: split at whitespace near target_size
            start = 0
            while start < sentence_len:
                end = min(start + target_size, sentence_len)
                # Try to break at whitespace near the end
                if end < sentence_len:
                    last_space = sentence.rfind(' ', start + target_size // 2, end)
                    if last_space != -1:
                        end = last_space
                piece = sentence[start:end].strip()
                if piece:
                    chunks.append(piece)
                start = end
            prev_sentences = [sentence[-target_size:]] if overlap_sentences > 0 else []
            current_chunk_sentences = list(prev_sentences)
            current_size = sum(len(s) + 1 for s in current_chunk_sentences) if current_chunk_sentences else 0
            continue

        current_chunk_sentences.append(sentence)
        current_size += sentence_len + (1 if current_size > 0 else 0)

    # Flush the last chunk
    if current_chunk_sentences:
        chunk_text = " ".join(current_chunk_sentences)
        if chunk_text.strip():
            if len(chunk_text) < min_size and chunks:
                # Merge small trailing chunk with previous
                chunks[-1] = chunks[-1] + " " + chunk_text
            else:
                chunks.append(chunk_text)

    return chunks
