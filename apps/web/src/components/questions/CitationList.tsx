import type { Citation } from '../../api/types'
export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null
  return (
    <section aria-labelledby="citations-heading">
      <h2 id="citations-heading">Citations</h2>
      <ol className="citationList">
        {citations.map((item) => (
          <li key={item.chunk_id}>
            <code className="citationPath">{item.path}</code>
            <span>
              Lines {item.start_line}–{item.end_line}
            </span>
            <span>
              Chunk{' '}
              <code>
                {item.chunk_id.length > 12 ? `${item.chunk_id.slice(0, 12)}…` : item.chunk_id}
              </code>
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}
