// Regenerates the API types from the backend: openapi.json (committed snapshot) and src/api/schema.d.ts.
// Run from web/: `npm run gen:api`. Uses the Python on PATH, or $PYTHON.
import { spawnSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'

const python = process.env.PYTHON ?? 'python'
const schema = spawnSync(python, ['-m', 'finsync.api', '--openapi'], { cwd: '..', encoding: 'utf8' })
if (schema.status !== 0) {
  console.error(schema.stderr || schema.error)
  process.exit(1)
}
writeFileSync('openapi.json', schema.stdout.replace(/\r\n/g, '\n'))

const types = spawnSync('npx', ['openapi-typescript', 'openapi.json', '-o', 'src/api/schema.d.ts'], {
  stdio: 'inherit',
  shell: true,
})
process.exit(types.status ?? 1)
