const fs = require('fs')
const path = require('path')
const knex = require('../knex')

async function runMigrations() {
  const migrationsDir = path.join(__dirname)
  const files = fs.readdirSync(migrationsDir).filter((f) => f.endsWith('.js') && f !== 'run.js')
  for (const file of files.sort()) {
    const migration = require(path.join(migrationsDir, file))
    if (migration.up) {
      console.log('Running', file)
      await migration.up(knex)
    }
  }
  console.log('Migrations complete')
  process.exit(0)
}

runMigrations().catch((err) => {
  console.error(err)
  process.exit(1)
})
