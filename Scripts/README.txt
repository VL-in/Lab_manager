================================================================================
  AI_lab_manager — assistente de laboratório (protótipo Docker)
================================================================================

Visão geral
-----------
Stack local com Docker Compose:
  • Flowise  — orquestração de fluxos / agentes (UI no host: veja a porta em FLOWISE_PORT)
  • Streamlit — interface web do laboratório: chat integrado ao Flowise, histórico de
    conversas persistente e exportação da conversa em DOCX
    (UI no host: veja a porta em STREAMLIT_PORT)

Nome do projeto Compose: ai_lab_manager.
Containers: ai_lab_manager_flowise, ai_lab_manager_streamlit.
Volumes nomeados:
  • Dados do Flowise: ai_lab_manager_flowise_data
  • Histórico de conversas do Streamlit: ai_lab_manager_streamlit_chat_data

Requisitos
----------
  • Docker Engine + Docker Compose v2 (por exemplo, Docker Desktop no Windows)
  • Portas livres no host. Padrão do projeto no .env.example:
      Flowise no host **3000**, Streamlit no host **8501**
    (a porta interna do Flowise dentro da rede Docker também é 3000; só o mapeamento
    no host muda se você definir outra FLOWISE_PORT, por exemplo 3001 em caso de conflito.)
  • Primeira execução: download da imagem flowiseai/flowise (pode demorar)

Como executar (evitando erro comum de pasta ou porta)
-------------------------------------------------------
1) Abra um terminal na pasta do repositório (onde está o docker-compose.yml):

   d:\Vanessa\AI_project\Lab_manager\Scripts

2) (Recomendado) Copie o arquivo de ambiente e confira as portas no host.

   Windows PowerShell:
     Copy-Item .env.example .env

   O modelo usa **FLOWISE_PORT=3000** e **STREAMLIT_PORT=8501** — em geral não é
   preciso mudar nada se essas portas estiverem livres.

   Só altere se aparecer erro do tipo "port is already allocated": por exemplo,
   **FLOWISE_PORT=3001** no .env (e use a mesma porta nas URLs do passo 4).

3) Inicie os serviços (build da imagem Streamlit na primeira vez):

     docker compose up --build

   Para rodar em segundo plano:

     docker compose up --build -d

4) Quando o Flowise estiver saudável, o Streamlit inicia automaticamente.
   Abra no navegador (com o .env.example padrão, sem mudar portas):

   • Streamlit:  http://localhost:8501
   • Flowise:    http://localhost:3000

   Se você mudou STREAMLIT_PORT ou FLOWISE_PORT no .env, use localhost com essas portas.

5) Parar os contêineres (mantém os volumes com dados do Flowise e do histórico de chat):

     docker compose down

   Para parar e apagar também os volumes persistentes declarados no compose (apaga
   fluxos salvos no Flowise e o ficheiro de conversas do Streamlit no volume
   ai_lab_manager_streamlit_chat_data):

     docker compose down -v

Segurança e partilha de repositório
-----------------------------------
  • Não coloque FLOWISE_CHATFLOW_ID, FLOWISE_API_KEY nem outros segredos em código
    Python ou em ficheiros versionados com valores reais.
  • A aplicação resolve esses valores só em tempo de execução, em
    apps/streamlit/env_config.py: primeiro variáveis de ambiente, depois chaves de
    mesmo nome em .streamlit/secrets.toml (à frente do comando streamlit run;
    esse ficheiro deve permanecer fora do Git — ver .gitignore).
  • O .env na pasta do compose também fica fora do Git; o .env.example serve só de
    modelo, sem segredos.
  • No docker-compose.yml, FLOWISE_CHATFLOW_ID e FLOWISE_API_KEY aparecem apenas como
    referências ${...} ao ambiente do host; valores reais ficam no seu .env local ou
    no sistema de secrets da sua CI/CD, nunca commitados.

Variáveis de ambiente (.env)
----------------------------
Definidas em .env.example — copie para .env na mesma pasta que o docker-compose.yml.

  STREAMLIT_PORT  — porta publicada no host para o Streamlit (padrão: 8501)
  FLOWISE_PORT    — porta publicada no host para o Flowise (padrão: 3000; use outra,
                    ex. 3001, só se a 3000 do host estiver ocupada)

Opcionais no .env (recomendadas para respostas reais do assistente no Streamlit):

  FLOWISE_CHATFLOW_ID — ID do flow no Flowise (Chatflow ou AgentFlow), usado em
                        POST .../api/v1/prediction/{id}. Se estiver vazio, a UI
                        funciona em modo demonstração (sem chamar o fluxo com ID).
  FLOWISE_API_KEY     — Chave de API do Flowise, se o servidor estiver configurado para
                        exigir autenticação (cabeçalho Authorization: Bearer ...).

Dentro do contêiner Streamlit (já definidas no compose; não precisa repetir no .env):

  FLOWISE_BASE_URL     — URL interna para chamadas HTTP entre contêineres
                         (http://flowise:3000)
  FLOWISE_PUBLIC_PORT  — só para mensagens na UI; precisa coincidir com o mapeamento
                         no host (o Compose repassa o valor de FLOWISE_PORT do .env)
  FLOWISE_CHATFLOW_ID  — repete o valor do .env do host (pode ficar vazio)
  FLOWISE_API_KEY      — repete o valor do .env do host (pode ficar vazio)
  LAB_CHAT_DATA_DIR    — diretório onde é gravado o histórico de conversas (/app/data),
                         persistido pelo volume streamlit_chat_data

Execução local do Streamlit (fora do Docker), na pasta apps/streamlit:

  • Opcional: LAB_CHAT_DATA_DIR — se não definida, o histórico grava-se em apps/streamlit/data/
    (pasta ignorada pelo Git; criada automaticamente).
  • FLOWISE_BASE_URL — por exemplo http://localhost:3000 se o Flowise estiver no host.
  • FLOWISE_CHATFLOW_ID / FLOWISE_API_KEY — mesma semântica que no compose.

Comportamento técnico
---------------------
  • O Flowise escuta na porta 3000 dentro da rede Docker; o mapeamento para o
    host é ${FLOWISE_PORT:-3000}:3000.
  • Healthcheck do Flowise: GET http://127.0.0.1:3000/api/v1/ping (curl dentro
    da imagem). O Streamlit depende de service_healthy para não iniciar antes
    do Flowise estar pronto.
  • Dados do Flowise (base SQLite e arquivos sob DATABASE_PATH) persistem no
    volume Docker ai_lab_manager_flowise_data montado em /root/.flowise.
  • Com o ID do flow definido no ambiente (ou em secrets), o Streamlit envia cada
    mensagem ao Flowise via HTTP POST em /api/v1/prediction/<id>, com corpo JSON que
    inclui "question" e "sessionId" (o ID da conversa no Streamlit, para memória por
    conversa no lado do Flowise quando o fluxo o suportar). Sem ID configurado, não
    há chamada a este endpoint: resposta de demonstração.
  • Histórico de conversas do Streamlit: ficheiro JSON chat_sessions.json sob
    LAB_CHAT_DATA_DIR (no Docker: /app/data, volume ai_lab_manager_streamlit_chat_data).

Interface Streamlit (funcional)
-------------------------------
  • Barra lateral: nova conversa, lista de conversas anteriores, exportar conversa (.docx),
    estado da ligação ao Flowise, remoção da conversa atual (se existir mais do que uma).
  • Área principal: cabeçalho discreto, painel do thread de mensagens e campo de entrada.
  • Dependências Python adicionais: requests, python-docx (ver apps/streamlit/requirements.txt).

Estrutura relevante do repositório
----------------------------------
  docker-compose.yml      — definição dos serviços
  .env.example            — modelo de variáveis
  apps/streamlit/         — código e Dockerfile do Streamlit
    app.py                — aplicação principal (layout chat + exportação)
    theme.py              — tema claro P&D (CSS injetado)
    env_config.py         — leitura de config sensível (ambiente + st.secrets; sem literais)
    chat_sessions.py      — modelo e persistência das conversas (JSON)
    flowise_client.py     — cliente HTTP para predição (recebe ID/chave já resolvidos)
    export_utils.py       — exportação DOCX
    Dockerfile            — copia o diretório apps/streamlit para a imagem (COPY . .)
    requirements.txt
    data/                 — apenas em execução local sem Docker: ficheiros de estado
                            (ignorado pelo Git; ver .gitignore)

Resolução de problemas
----------------------
  • "port is already allocated" / porta em uso:
      Altere STREAMLIT_PORT ou FLOWISE_PORT no arquivo .env (ex.: FLOWISE_PORT=3001
      em vez de 3000) e execute de novo: docker compose up --build

  • Streamlit não sobe e fica aguardando o Flowise:
      Verifique os logs: docker compose logs -f flowise
      Se a imagem do Flowise for antiga e não tiver curl, o healthcheck pode falhar.
      Nesse caso, atualize a imagem (docker compose pull flowise) ou entre em contato
      com quem mantém o projeto para ajustar o healthcheck no docker-compose.yml.

  • Erro ao fazer build do Streamlit:
      Confirme que você está na pasta Scripts e que apps/streamlit contém Dockerfile,
      requirements.txt, app.py e os módulos Python referenciados na secção de estrutura.

  • Chat em modo demonstração ou sem resposta do fluxo:
      Confirme FLOWISE_CHATFLOW_ID no .env (ID correto do Chatflow/AgentFlow no Flowise) e que o
      fluxo está publicado/ativo. Em caso de 401/403, configure FLOWISE_API_KEY conforme
      a instância do Flowise.

AgentFlow + LM Studio (fluxo recomendado)
-----------------------------------------
  • Fluxo suportado no projeto: AgentFlow no Flowise orquestrando chamadas ao LLM local
    via LM Studio.
  • Nesse cenário, o valor em FLOWISE_CHATFLOW_ID continua obrigatório para respostas reais:
    use o ID que aparece no endpoint de prediction do AgentFlow
    (/api/v1/prediction/{id}).
  • Onde obter o ID na UI do Flowise:
      1) Abra Agentflows e selecione o fluxo.
      2) Abra Share/API/Embed.
      3) Copie o endpoint e extraia o {id}.
  • Exemplo no .env:
      FLOWISE_CHATFLOW_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
      FLOWISE_API_KEY=... (se a instância exigir autenticação)

  • Ver estado dos serviços:
      docker compose ps

  • Reconstruir só o Streamlit depois de mudar o código:
      docker compose build --no-cache streamlit; docker compose up -d

Notas para evolução (fora deste compose)
----------------------------------------
  • LM Studio no host (modelos locais): os contêineres acessam o host em geral
    via host.docker.internal no Windows; isso será documentado quando integrar
    modelos locais diretamente neste compose.
  • Próximos passos típicos: painel de dados ou anexos no chat, streaming de tokens se o
    fluxo Flowise suportar.

================================================================================
  Fim do README
================================================================================
