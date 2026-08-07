export type PlannedToolCategory =
  'Security' | 'Code Quality' | 'Testing' | 'Collaboration' | 'Reporting'

export type PlannedTool = {
  id: string
  name: string
  category: PlannedToolCategory
  summary: string
  capabilities: string[]
  expectedInputs: string[]
  expectedOutputs: string[]
  usefulness: string
  status: 'coming-soon'
  accent: 'green' | 'blue' | 'amber' | 'purple'
}

export const plannedTools: readonly PlannedTool[] = [
  {
    id: 'security-scanner',
    name: 'Security Scanner',
    category: 'Security',
    summary: 'Surface potential code and configuration security review leads.',
    capabilities: [
      'Identify potentially vulnerable code patterns',
      'Detect insecure configuration',
      'Locate dangerous execution paths',
      'Provide exact file and line references',
      'Generate review recommendations',
    ],
    expectedInputs: ['A completed persisted repository analysis'],
    expectedOutputs: ['Potential findings with evidence', 'Qualified review recommendations'],
    usefulness:
      'Helps reviewers find security-sensitive areas without presenting the result as a security audit.',
    status: 'coming-soon',
    accent: 'amber',
  },
  {
    id: 'secret-scanner',
    name: 'Secret Scanner',
    category: 'Security',
    summary: 'Locate and safely report potentially exposed credentials.',
    capabilities: [
      'Detect exposed API keys, tokens, passwords, and credentials',
      'Redact detected values',
      'Identify the exact file and line',
      'Recommend rotation and cleanup steps',
    ],
    expectedInputs: ['Eligible persisted text files'],
    expectedOutputs: ['Redacted potential-secret findings', 'Rotation and cleanup guidance'],
    usefulness:
      'Supports rapid credential-hygiene review while keeping suspected values concealed.',
    status: 'coming-soon',
    accent: 'purple',
  },
  {
    id: 'dependency-audit',
    name: 'Dependency Audit',
    category: 'Security',
    summary: 'Review dependency manifests for upgrade and vulnerability leads.',
    capabilities: [
      'Inspect dependency manifests',
      'Identify outdated or vulnerable dependencies',
      'Classify severity',
      'Show affected packages and versions',
      'Recommend safe upgrade paths',
    ],
    expectedInputs: ['Persisted dependency manifests', 'Future trusted advisory data'],
    expectedOutputs: ['Affected package review list', 'Qualified upgrade paths'],
    usefulness:
      'Would help maintainers prioritize dependency work using traceable manifest evidence.',
    status: 'coming-soon',
    accent: 'blue',
  },
  {
    id: 'license-review',
    name: 'License Review',
    category: 'Reporting',
    summary: 'Summarize dependency licensing and compatibility review leads.',
    capabilities: [
      'Detect dependency licenses',
      'Identify missing or potentially incompatible licenses',
      'Summarize repository licensing risks',
      'Link results to dependency files',
    ],
    expectedInputs: ['Persisted manifests and license files'],
    expectedOutputs: ['License inventory', 'Potential compatibility review leads'],
    usefulness:
      'Would make licensing questions easier to investigate without replacing legal review.',
    status: 'coming-soon',
    accent: 'purple',
  },
  {
    id: 'complexity-analysis',
    name: 'Complexity Analysis',
    category: 'Code Quality',
    summary: 'Highlight probable maintainability hotspots and refactoring candidates.',
    capabilities: [
      'Estimate file and function complexity',
      'Identify highly complex modules',
      'Highlight maintainability hotspots',
      'Suggest refactoring candidates',
    ],
    expectedInputs: ['Persisted parsed source and symbols'],
    expectedOutputs: ['Bounded complexity signals', 'Refactoring candidates with evidence'],
    usefulness:
      'Would focus engineering attention on code that may be costly to understand or change.',
    status: 'coming-soon',
    accent: 'green',
  },
  {
    id: 'test-coverage-intelligence',
    name: 'Test Coverage Intelligence',
    category: 'Testing',
    summary: 'Connect changed source areas with likely tests and possible gaps.',
    capabilities: [
      'Connect source files with likely tests',
      'Identify areas that may lack coverage',
      'Summarize untested change-impact areas',
      'Show test recommendations',
    ],
    expectedInputs: [
      'Persisted source, test classification, and static relationships',
      'Future measured coverage data when available',
    ],
    expectedOutputs: ['Likely source-to-test relationships', 'Qualified test recommendations'],
    usefulness:
      'Would help scope test review while never claiming measured coverage without coverage data.',
    status: 'coming-soon',
    accent: 'green',
  },
  {
    id: 'pull-request-review',
    name: 'Pull Request Review Assistant',
    category: 'Collaboration',
    summary: 'Organize a change set into a structured review briefing.',
    capabilities: [
      'Summarize changed files',
      'Identify affected modules',
      'Flag risky modifications',
      'Suggest review questions',
      'Provide a structured review checklist',
    ],
    expectedInputs: ['A future trusted pull request diff', 'Persisted repository intelligence'],
    expectedOutputs: ['Change summary', 'Review questions and checklist'],
    usefulness:
      'Would give reviewers an evidence-backed starting point without approving changes automatically.',
    status: 'coming-soon',
    accent: 'blue',
  },
  {
    id: 'change-risk',
    name: 'Change Risk Analysis',
    category: 'Code Quality',
    summary: 'Estimate bounded direct and probable indirect change impact.',
    capabilities: [
      'Estimate likely change impact',
      'Identify highly connected files',
      'Locate affected tests',
      'Classify direct and probable indirect impact',
      'Highlight uncertainty',
    ],
    expectedInputs: ['Selected persisted files or modules', 'Persisted static dependency evidence'],
    expectedOutputs: ['Qualified impact map', 'Likely tests and uncertainty notes'],
    usefulness: 'Would extend current impact intelligence into a focused planning workflow.',
    status: 'coming-soon',
    accent: 'amber',
  },
  {
    id: 'repository-comparison',
    name: 'Repository Comparison',
    category: 'Collaboration',
    summary: 'Compare two trusted analyses or commits.',
    capabilities: [
      'Compare two analyses or commits',
      'Show new and resolved findings',
      'Show score changes',
      'Identify dependency changes',
      'Summarize architecture differences',
    ],
    expectedInputs: ['Two completed persisted analysis snapshots'],
    expectedOutputs: ['Evidence-linked differences', 'Qualified architecture-change summary'],
    usefulness:
      'Would help teams understand how repository intelligence changed between revisions.',
    status: 'coming-soon',
    accent: 'blue',
  },
  {
    id: 'architecture-export',
    name: 'Architecture Report Export',
    category: 'Reporting',
    summary: 'Package repository intelligence into a shareable report.',
    capabilities: [
      'Generate a repository overview report',
      'Include architecture, findings, quality, and dependencies',
      'Preserve exact source references',
      'Support a future PDF or HTML export',
    ],
    expectedInputs: ['A completed persisted analysis'],
    expectedOutputs: ['Future PDF or HTML report with source references'],
    usefulness:
      'Would make grounded repository intelligence easier to share with contributors and reviewers.',
    status: 'coming-soon',
    accent: 'purple',
  },
]

export const plannedToolCategories: readonly PlannedToolCategory[] = [
  'Security',
  'Code Quality',
  'Testing',
  'Collaboration',
  'Reporting',
]
