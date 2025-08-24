# Local N8N Development Lab

This repository is a collection of configuration files that define a comprehensive `n8n` automation environment with an intelligent AI agent. It includes N8N Community Edition, a Postgres database, and an AI-powered workflow agent that can create n8n workflows from natural language descriptions. Compiled by Kura Labs, it is intended to faciliate local N8N development and experimentation for learning and instruction purposes.

## Quickstart

> **Prerequisites**
>
> In order to use the lab, you must have, at a minimum, the following installed on your local machine:
> - [`git`](https://git-scm.com/downloads)
> - [`docker`](https://www.docker.com/get-started/) and [`docker compose`](https://www.docker.com/get-started/)
> - **OpenRouter API Key** (for AI agent functionality) - Get one at [openrouter.ai](https://openrouter.ai)
>
> *Note: To run the lab locally, you should have >=16GB of System Memory on your machine. It may run on machines with less memory, but performance may be poor.*


1. Clone the repo

In your terminal/commandline, navigate to the directory you wish to save the lab files to. Then execute the following to clone the repo to your system:

```bash
git clone https://github.com/Codon-Ops/n8n-lab.git
cd n8n-lab
```

2. Set up your environment

Configure the OpenRouter API key for the AI agent functionality:

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenRouter API key
# OPENROUTER_API_KEY=your_api_key_here
```

3. Start the services

With the repository downloaded and configured, you can now start up N8N and all services including the intelligent agent:

```bash
docker compose up -d
```

This will set up your complete lab infrastructure including:
- n8n workflow automation platform
- PostgreSQL database
- pgAdmin database management
- **AI Agent API** for natural language workflow creation
- Reverse proxy for easy access

The setup may take a few minutes to complete depending on your system.

4. Access the applications

Once the lab has finished building, you can access:

- **n8n Interface**: http://n8n.localhost (register yourself here)
- **AI Agent API**: http://localhost:8001 (see API_GUIDE.md for usage)
- **Database Admin**: http://database.n8n.localhost

That's it! You're ready to create workflows both manually through the n8n interface and automatically using natural language with the AI agent!

## Intelligent Workflow Creation

The lab now includes an AI agent that can create n8n workflows from natural language descriptions. Here are some examples:

### Creating Workflows with Natural Language

```bash
# Example 1: Email automation
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a workflow that sends me an email when someone fills out my contact form",
    "activate": false
  }'

# Example 2: Data synchronization  
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Sync new Shopify orders to my Airtable database every hour",
    "activate": true
  }'

# Example 3: Social media automation
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Post my new blog articles to Twitter and LinkedIn automatically",
    "activate": false
  }'
```

### Searching Workflow Templates

Before creating new workflows, you can search existing templates:

```bash
curl -X POST http://localhost:8001/dryrun \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need to process customer feedback forms and send notifications"
  }'
```

### Health Monitoring

Check the status of all services:

```bash
curl http://localhost:8001/health
```

## Architecture Overview

The lab consists of 5 interconnected services:

1. **n8n** (Port 5678): Main workflow automation platform
2. **PostgreSQL** (Port 5432): Database for n8n data persistence  
3. **pgAdmin** (Port 8080): Web-based database administration
4. **Caddy**: Reverse proxy for clean URL routing
5. **Agent API** (Port 8001): **NEW!** AI-powered workflow creation service

### Agent API Features

- **Natural Language Processing**: Describe workflows in plain English
- **Template Search**: Find existing workflow templates by functionality
- **Automatic Creation**: Generate and optionally activate workflows in n8n
- **Health Monitoring**: Check connectivity to all services
- **LangGraph Integration**: State machine for intelligent workflow processing
- **OpenRouter LLMs**: Supports multiple AI models for different use cases

## Complete Documentation

For detailed information, see:
- `CLAUDE.md`: Complete development guide with all commands and configurations
- `API_GUIDE.md`: Comprehensive API documentation with examples
- `agent-api/README_TESTING.md`: Testing guide for the agent functionality

## Set up Database Credentials & Admin interface

As part of this lab, you have access to your own Postgres database and an administration tool called PgAdmin. PgAdmin provides a user interface that allows you to explore your database, run queries, and perform general administrative tasks.

Your N8N instance uses Postgres to save your credentials, past executions, and workflows. You can also use it for any applications you build.

### Set up Postgres Credentials in N8N

1. Go to http://n8n.localhost/home/workflows

2. Click on `Credentials` and then `Add first credential`:

> **Note**: If you already have credentials added, go to the `Create_Workflow` button in the top right-hand corner, click the drop-down arrow, then click `Create Credential`

![n8n Workflows Page](/assets/AddCredential-1.jpg)

3. Search for and select `Postgres`:

![n8n add credentials](/assets/AddCredential-2.jpg)

4. When the `Connection` dialogue comes up, fill in the connection details for the database:

* Host: `postgres`
* Database: `n8n`
* User: `kura`
* Password: `password`

> **Note**: You will only need to fill in these fields. Leave everything else as-is.

![n8n Postgres Credential Log](/assets/AddCredential-3.jpg)

5. Save the credentials and take note of the connection test. After saving your credentials, you should see a connection result like the screen below:

![n8n Postgres Credential Success](/assets/AddCredential-4.jpg)


Now you've saved your database credentials to your n8n instance! Next we'll set up PgAdmin so you can interact directly with the database. 

### Set up PgAdmin

1. Go to http://database.n8n.localhost and login using the credentials below:

* Username: `student@kuralabs.com`
* Password: `password`

![PgAdmin Login Page](/assets/PgAdmin-1.jpg)

2. Once you're logged in, go to the top left corner to `Servers`. Right-click that, then go to `Register` -> `Server...`:

![PgAdmin Login Page](/assets/PgAdmin-2.jpg)

3. You should be on the `General` tab in the `Register Server` dialog. Give your server a memorable name - this is the label that will be used in the UI when you want to check your database:

![PgAdmin Login Page](/assets/PgAdmin-3.jpg)

4. In that same dialog box, click on the `Connection` tab, fill in the database credentials like you did before, and then click `Save`:

* Host name/address: `postgres`
* Maintenance Database: `n8n`
* Username: `kura`
* Password: `password`

![PgAdmin Login Page](/assets/PgAdmin-4.jpg)

5. Now you have successfully connected PgAdmin to your database and can view the tables in there using the `Object Explorer` in the left-hand corner:

![PgAdmin Login Page](/assets/PgAdmin-5.jpg)

That's it for the database connections - you're all set!

## Useful links

* `n8n`: http://n8n.localhost
* `n8n database admin tool`: http://database.n8n.localhost