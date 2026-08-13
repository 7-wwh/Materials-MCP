#!/usr/bin/env python3
"""
Transform scraped JSON results into normalized, chunked CSV and Parquet files.

Processes output from tavily_search.py or exa_search.py, cleans boilerplate,
normalizes formatting, splits into semantic chunks, and exports to CSV/Parquet.

Usage:
    python scrape_to_structured.py \
      --input data/query-slug/tavily_20260808-120000.json \
      --output-dir data/query-slug/csv/ \
      --format csv+parquet \
      --chunk-size 300 \
      --normalize
"""

import json
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass, asdict

@dataclass
class ContentChunk:
    """Represents one normalized chunk of extracted content."""
    source_url: str
    domain: str
    title: str
    chunk_id: int
    chunk_text: str
    chunk_order: int
    word_count: int
    char_count: int
    extracted_at: str
    provider: str
    query: str


class ContentCleaner:
    """Removes boilerplate and normalizes text from scraped pages."""
    
    # Patterns for common boilerplate/noise
    BOILERPLATE_PATTERNS = [
        r'(?i)cookie\s+(?:policy|notice|consent)',
        r'(?i)(?:subscribe|sign\s+up).*newsletter',
        r'(?i)(?:advertisement|sponsored\s+content)',
        r'(?i)(?:related\s+articles|recommended\s+for\s+you)',
        r'(?i)(?:share\s+on|follow\s+us)',
        r'^\s*(?:previous|next|page\s+\d+)',
        r'(?:javascript|jquery|async)',
        r'<!DOCTYPE|<html|<body|<script|<style',
        r'href=|onclick=|onload=',
    ]
    
    # Patterns to remove entirely
    REMOVE_PATTERNS = [
        r'\[[\w\s]*ad\s*\]',  # [ad], [advertisement]
        r'©.*?\d{4}',  # copyright notices
        r'(?:Terms?|Privacy|Cookie).*?(?:\.|$)',  # T&C footers
    ]
    
    def __init__(self, normalize: bool = True):
        self.normalize = normalize
        self.boilerplate_regex = re.compile(
            '|'.join(self.BOILERPLATE_PATTERNS),
            re.IGNORECASE | re.MULTILINE
        )
        self.remove_regex = re.compile(
            '|'.join(self.REMOVE_PATTERNS),
            re.IGNORECASE | re.MULTILINE
        )
    
    def clean(self, text: str) -> str:
        """Clean boilerplate and normalize text."""
        if not text:
            return ""
        
        # Remove HTML tags and entities
        text = re.sub(r'<[^>]+>', '', text)
        text = self._decode_entities(text)
        
        # Remove boilerplate sections
        lines = text.split('\n')
        cleaned_lines = [
            line for line in lines
            if not self.boilerplate_regex.search(line)
        ]
        text = '\n'.join(cleaned_lines)
        
        # Remove specific patterns
        text = self.remove_regex.sub('', text)
        
        if self.normalize:
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text)  # collapse whitespace
            text = re.sub(r'\n\s*\n', '\n', text)  # normalize paragraph breaks
            text = text.strip()
        
        return text
    
    def _decode_entities(self, text: str) -> str:
        """Decode common HTML entities."""
        entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&hellip;': '...',
            '&mdash;': '—',
            '&ndash;': '–',
        }
        for entity, char in entities.items():
            text = text.replace(entity, char)
        return text


class ContentChunker:
    """Splits long text into semantic chunks."""
    
    def __init__(self, chunk_size: int = 300):
        self.chunk_size = chunk_size
    
    def chunk(self, text: str, order_offset: int = 0) -> List[Tuple[str, int]]:
        """
        Split text into chunks. Returns list of (chunk_text, chunk_order) tuples.
        
        Strategy:
        1. Split on sentence boundaries (. ! ?)
        2. If sentence is too long, split on paragraph breaks
        3. If still too long, split on word boundaries
        4. Last resort: hard split
        """
        if not text:
            return []
        
        chunks = []
        chunk_order = order_offset
        
        # Try sentence-level splitting first
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = ""
        
        for sentence in sentences:
            candidate = current_chunk + (" " if current_chunk else "") + sentence
            
            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
            else:
                # Current chunk is full
                if current_chunk:
                    chunks.append((current_chunk, chunk_order))
                    chunk_order += 1
                
                # If single sentence is too long, split it further
                if len(sentence) > self.chunk_size:
                    sub_chunks = self._split_long_sentence(sentence)
                    for sub_chunk in sub_chunks:
                        chunks.append((sub_chunk, chunk_order))
                        chunk_order += 1
                    current_chunk = ""
                else:
                    current_chunk = sentence
        
        # Add remainder
        if current_chunk.strip():
            chunks.append((current_chunk, chunk_order))
        
        return chunks
    
    def _split_long_sentence(self, sentence: str) -> List[str]:
        """Split a single long sentence on word/phrase boundaries."""
        words = sentence.split()
        chunks = []
        current = []
        
        for word in words:
            candidate = ' '.join(current + [word])
            if len(candidate) <= self.chunk_size:
                current.append(word)
            else:
                if current:
                    chunks.append(' '.join(current))
                current = [word]
        
        if current:
            chunks.append(' '.join(current))
        
        return chunks


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain
    except:
        return "unknown"


def process_scrape_results(
    input_path: Path,
    chunk_size: int = 300,
    normalize: bool = True,
) -> List[ContentChunk]:
    """Load JSON results and transform into list of ContentChunks."""
    
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    if data.get('status') != 'ok':
        raise ValueError(f"Input JSON status is not 'ok': {data.get('status')}")
    
    results = data.get('results', [])
    provider = data.get('provider', 'unknown')
    query = data.get('query', '')
    
    cleaner = ContentCleaner(normalize=normalize)
    chunker = ContentChunker(chunk_size=chunk_size)
    
    chunks = []
    now = datetime.utcnow().isoformat() + 'Z'
    
    for result in results:
        url = result.get('url', '')
        title = result.get('title', '')
        content = result.get('content', '')
        
        # Skip results without content
        if not content or not content.strip():
            continue
        
        # Clean content
        cleaned_content = cleaner.clean(content)
        if not cleaned_content:
            continue
        
        # Split into chunks
        chunk_list = chunker.chunk(cleaned_content)
        domain = extract_domain(url)
        
        for chunk_idx, (chunk_text, chunk_order) in enumerate(chunk_list):
            if chunk_text.strip():  # Only add non-empty chunks
                chunk = ContentChunk(
                    source_url=url,
                    domain=domain,
                    title=title,
                    chunk_id=chunk_idx,
                    chunk_text=chunk_text.strip(),
                    chunk_order=chunk_order,
                    word_count=len(chunk_text.split()),
                    char_count=len(chunk_text),
                    extracted_at=now,
                    provider=provider,
                    query=query,
                )
                chunks.append(chunk)
    
    return chunks


def save_csv(chunks: List[ContentChunk], output_path: Path) -> None:
    """Save chunks to CSV file."""
    import csv
    
    if not chunks:
        print(f"Warning: No chunks to save to CSV")
        return
    
    fieldnames = list(asdict(chunks[0]).keys())
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for chunk in chunks:
            writer.writerow(asdict(chunk))
    
    print(f"✓ Saved CSV: {output_path} ({len(chunks)} rows)")


def save_parquet(chunks: List[ContentChunk], output_path: Path) -> None:
    """Save chunks to Parquet file."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        print("Warning: pyarrow not installed. Skipping Parquet export.")
        print("  Install with: pip install pyarrow")
        return
    
    if not chunks:
        print(f"Warning: No chunks to save to Parquet")
        return
    
    # Convert chunks to dict format for Arrow
    data_dict = {field: [] for field in asdict(chunks[0]).keys()}
    for chunk in chunks:
        chunk_dict = asdict(chunk)
        for key, value in chunk_dict.items():
            data_dict[key].append(value)
    
    # Create Arrow table and write
    table = pa.table(data_dict)
    pq.write_table(table, output_path)
    
    print(f"✓ Saved Parquet: {output_path} ({len(chunks)} rows)")


def main():
    parser = argparse.ArgumentParser(
        description="Transform scraped JSON results into normalized CSV/Parquet"
    )
    parser.add_argument(
        '--input', 
        type=Path, 
        required=True,
        help='Path to input JSON file from tavily_search.py or exa_search.py'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        required=True,
        help='Directory to save CSV/Parquet files'
    )
    parser.add_argument(
        '--format',
        choices=['csv', 'parquet', 'csv+parquet', 'both'],
        default='both',
        help='Export format (default: both)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=300,
        help='Target chunk size in characters (default: 300)'
    )
    parser.add_argument(
        '--normalize',
        action='store_true',
        default=True,
        help='Enable whitespace normalization (default: true)'
    )
    parser.add_argument(
        '--no-normalize',
        action='store_false',
        dest='normalize',
        help='Disable normalization'
    )
    
    args = parser.parse_args()
    
    # Validate input
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Process
        print(f"Processing: {args.input}")
        chunks = process_scrape_results(
            args.input,
            chunk_size=args.chunk_size,
            normalize=args.normalize,
        )
        
        if not chunks:
            print("Error: No content chunks extracted from input")
            return 1
        
        print(f"✓ Extracted {len(chunks)} chunks from {len(set(c.source_url for c in chunks))} sources")
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        base_name = f"results_{timestamp}"
        
        # Export
        export_formats = args.format.replace('+', ',').split(',')
        if 'both' in export_formats:
            export_formats = ['csv', 'parquet']
        
        for fmt in export_formats:
            if fmt == 'csv':
                csv_path = args.output_dir / f"{base_name}.csv"
                save_csv(chunks, csv_path)
            elif fmt == 'parquet':
                pq_path = args.output_dir / f"{base_name}.parquet"
                save_parquet(chunks, pq_path)
        
        # Summary
        domains = set(c.domain for c in chunks)
        total_words = sum(c.word_count for c in chunks)
        print(f"\nSummary:")
        print(f"  Domains: {len(domains)} ({', '.join(sorted(domains)[:3])}{'...' if len(domains) > 3 else ''})")
        print(f"  Total words: {total_words:,}")
        print(f"  Avg chunk size: {total_words // len(chunks)} words")
        
        return 0
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())