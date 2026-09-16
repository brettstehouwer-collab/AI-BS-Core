module.exports = {
  apps: [
    {
      name: "AI-BS-Backend",
      script: "AI_BS_Backend.py",
      interpreter: ".venv/Scripts/python.exe",
      cwd: "G:/Stehouwer_Server/AI-BS/backend",
      watch: false,
      autorestart: true,
      max_restarts: 10,
      log_date_format: "YYYY-MM-DD HH:mm Z"
    },
    {
      name: "Bullshit-Trainer",
      script: "bullshit_trainer.py",
      interpreter: ".venv/Scripts/python.exe",
      cwd: "G:/Stehouwer_Server/AI-BS/backend",
      watch: false,
      autorestart: true,
      max_restarts: 10
    },
    {
      name: "DB-Writer-Daemon",
      script: "db_writer_daemon.py",
      interpreter: ".venv/Scripts/python.exe",
      cwd: "G:/Stehouwer_Server/AI-BS/backend",
      watch: false,
      autorestart: true,
      max_restarts: 10
    },
    {
      name: "Bullshit-Senses",
      script: "bullshit_senses.py",
      interpreter: ".venv/Scripts/python.exe",
      cwd: "G:/Stehouwer_Server/AI-BS/backend",
      watch: false,
      autorestart: true,
      max_restarts: 10
    },
    {
      name: "Matrix-Frontend",
      script: "npm.cmd",
      args: "run dev",
      cwd: "G:/Stehouwer_Server/AI-BS/frontend",
      watch: false,
      autorestart: true,
      max_restarts: 10
    }
  ]
};
