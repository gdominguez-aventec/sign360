// PM2, com el frontal d'avsis. Un sol procés: el servidor és petit i comparteix
// màquina amb customers i el helpdesk.
module.exports = {
  apps: [
    {
      name: 'Sign360 Frontend',
      script: './.output/server/index.mjs',
      cwd: '/var/www/sign360/frontend',
      instances: 1,
      exec_mode: 'cluster',
      env: {
        NODE_ENV: 'production',
        HOST: '127.0.0.1',
        PORT: 3006,
      },
    },
  ],
}
