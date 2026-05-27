exports.up = async function(knex) {
  await knex.schema.createTable('users', (table) => {
    table.increments('id').primary()
    table.string('email').notNullable().unique()
    table.string('password_hash').notNullable()
    table.string('role').defaultTo('admin')
    table.boolean('active').defaultTo(true)
    table.timestamp('created_at').defaultTo(knex.fn.now())
  })

  await knex.schema.createTable('colaboradores', (table) => {
    table.increments('id').primary()
    table.string('email').notNullable().unique()
    table.string('role').defaultTo('colaborador')
    table.boolean('active').defaultTo(true)
    table.timestamp('created_at').defaultTo(knex.fn.now())
  })
}

exports.down = async function(knex) {
  await knex.schema.dropTableIfExists('colaboradores')
  await knex.schema.dropTableIfExists('users')
}
