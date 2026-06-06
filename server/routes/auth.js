const express = require('express')
const bcrypt = require('bcrypt')
const jwt = require('jsonwebtoken')
const knex = require('../knex')

const router = express.Router()
const JWT_SECRET = process.env.JWT_SECRET || 'devsecret'

router.post('/register', async (req, res) => {
  const { email, password } = req.body
  if (!email || !password) return res.status(400).json({ error: 'Email and password required' })

  const existing = await knex('users').where({ email }).first()
  if (existing) return res.status(400).json({ error: 'User already exists' })

  const hash = await bcrypt.hash(password, 10)
  const [id] = await knex('users').insert({ email, password_hash: hash, role: 'admin' })
  res.json({ id, email })
})

router.post('/login', async (req, res) => {
  const { email, password } = req.body
  if (!email || !password) return res.status(400).json({ error: 'Email and password required' })

  const user = await knex('users').where({ email }).first()
  if (!user) return res.status(401).json({ error: 'Invalid credentials' })

  const ok = await bcrypt.compare(password, user.password_hash)
  if (!ok) return res.status(401).json({ error: 'Invalid credentials' })

  const token = jwt.sign({ sub: user.id, role: user.role, email: user.email }, JWT_SECRET, { expiresIn: '7d' })
  res.json({ token })
})

module.exports = router
