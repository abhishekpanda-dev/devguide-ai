import type { Repository } from '../../api/types'
import { StatusBadge } from '../feedback/StatusBadge'

export function RepositoryFacts({ repository }: { repository: Repository }) {
  return (
    <dl className="facts">
      <div>
        <dt>Status</dt>
        <dd>
          <StatusBadge status={repository.status} />
        </dd>
      </div>
      <div>
        <dt>Source</dt>
        <dd>
          <a href={repository.source_url} target="_blank" rel="noreferrer">
            {repository.normalized_url}
          </a>
        </dd>
      </div>
      <div>
        <dt>Default branch</dt>
        <dd>
          <code>{repository.default_branch ?? 'Not available'}</code>
        </dd>
      </div>
      <div>
        <dt>Commit</dt>
        <dd>
          <code>{repository.latest_commit_sha ?? 'Not available'}</code>
        </dd>
      </div>
    </dl>
  )
}
