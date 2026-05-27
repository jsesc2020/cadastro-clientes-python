const express = require('express')
const knex = require('../knex')
const router = express.Router()

router.get('/', async (req, res) => {
  const data = await knex('colaboradores').select('id', 'email', 'role', 'active', 'created_at')
  res.json(data)
})

router.post('/', async (req, res) => {
  const { email, role } = req.body
  if (!email) return res.status(400).json({ error: 'Email required' })
  const [id] = await knex('colaboradores').insert({ email, role: role || 'colaborador', active: true })
  const created = await knex('colaboradores').where({ id }).first()
  res.json(created)
})

router.put('/:id/active', async (req, res) => {
  const { id } = req.params
  const { active } = req.body
  await knex('colaboradores').where({ id }).update({ active })
  const updated = await knex('colaboradores').where({ id }).first()
  res.json(updated)
})

module.exports = router
