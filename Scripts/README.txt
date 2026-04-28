================================================================================
  AI_lab_manager — assistente de laboratório (protótipo Docker)
================================================================================

Declaração do desafio
---------------------
Ideia:
Gestão e consulta de dados de projetos de pesquisa e desenvolvimento voltada a imunoensaios.

Pergunta essencial:
Como o agente de IA pode facilitar o dia a dia dos pesquisadores e tecnologistas, resolvendo a dor de buscar, arquivo por arquivo, dados sobre experimentos passados?

Desafio:
O Agente de IA irá consultar o roll de documentos gerados, sintetizar a resposta com o dado encontrado, além de trazer a localidade (em qual documento 
foi encontrado) para assegurar rastreabilidade e confiabilidade.

Justificativa pessoal:
Não aguento mais ficar indo de arquivo por arquivo para procurar informações. Além disso, é fácil acumular erros quando se registra muitos dados, então
podemos usar a IA para fazer a verificação de dados sempre que precisar.


Visão geral
-----------
Stack local com Docker Compose:
  • Flowise  — orquestração de fluxos / agentes (UI no host: veja a porta em FLOWISE_PORT)
  • Streamlit — interface web do laboratório: chat integrado ao Flowise (respostas em
    streaming quando o fluxo suporta SSE), histórico persistente, exportação DOCX e
    aba para consulta a dados ELISA em Excel via DuckDB
    (UI no host: veja a porta em STREAMLIT_PORT)
  • ChromaDB — vetor store local para RAG e embeddings textuais
    (API no host: veja a porta em CHROMA_PORT)

Nome do projeto Compose: ai_lab_manager.
Containers: ai_lab_manager_flowise, ai_lab_manager_streamlit, ai_lab_manager_chroma.
Volumes nomeados:
  • Dados do Flowise: ai_lab_manager_flowise_data
  • Histórico de conversas do Streamlit: ai_lab_manager_streamlit_chat_data
  • Vetores/coleções Chroma: ai_lab_manager_chroma_data

Progresso atual (implementado e validado)
-----------------------------------------
  • Streamlit + Flowise + Chroma em execução no Docker com serviços saudáveis.
  • RAG operacional no Flowise com upsert para Chroma local.
  • Embeddings no LM Studio com modelo `mxbai-embed-large-v1` (1024 dimensões).
  • Configuração validada de upsert:
      - batch size: 20
      - timeout: 360
      - Vector Store: Chroma local (`http://chroma:8000`)
      - top-k: 5
  • Pipeline de carga no Flowise validado com:
      - Docx File Loader
      - Token Text Splitter (`encoding: gpt2`)
      - chunk size: 300
      - chunk overlap: 100
      - dois loaders separados: sensibilização e otimização
  • Streamlit: streaming de tokens (API de predição com `streaming: true` + eventos SSE
    no formato do Flowise), tema com espaçamento para o cabeçalho nativo não cobrir as
    abas, área de chat com rolagem e aba "Dados ELISA (DuckDB)" (pré-visualização,
    SQL, exportação CSV, gráficos rápidos opcionais).

Requisitos
----------
  • Docker Engine + Docker Compose v2 (por exemplo, Docker Desktop no Windows)
  • Portas livres no host. Padrão do projeto no .env.example:
      Flowise no host **3000**, Streamlit no host **8501**, Chroma no host **8000**
    (a porta interna do Flowise dentro da rede Docker também é 3000; só o mapeamento
    no host muda se você definir outra FLOWISE_PORT, por exemplo 3001 em caso de conflito.)
  • Primeira execução: download das imagens flowiseai/flowise e chromadb/chroma
    (pode demorar)

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
   • Chroma:     http://localhost:8000

   Se você mudou STREAMLIT_PORT ou FLOWISE_PORT no .env, use localhost com essas portas.

5) Parar os contêineres (mantém os volumes com dados do Flowise e do histórico de chat):

     docker compose down

   Para parar e apagar também os volumes persistentes declarados no compose (apaga
   fluxos salvos no Flowise e o arquivo de conversas do Streamlit no volume
   ai_lab_manager_streamlit_chat_data):

     docker compose down -v

Segurança e compartilhamento de repositório
-----------------------------------
  • Não coloque FLOWISE_CHATFLOW_ID, FLOWISE_API_KEY nem outros segredos em código
    Python ou em arquivos versionados com valores reais.
  • A aplicação resolve esses valores só em tempo de execução, em
    apps/streamlit/env_config.py: primeiro variáveis de ambiente, depois chaves de
    mesmo nome em .streamlit/secrets.toml (à frente do comando streamlit run;
    esse arquivo deve permanecer fora do Git — ver .gitignore).
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
  CHROMA_PORT     — porta publicada no host para a API do Chroma (padrão: 8000)
  CHROMA_COLLECTION — coleção padrão de documentos para o RAG (padrão: lab_docs)
  LMSTUDIO_BASE_URL — endpoint OpenAI-compatible do LM Studio
                      (padrão Docker/Windows: http://host.docker.internal:1234/v1)
  LMSTUDIO_EMBEDDING_MODEL — modelo de embeddings usado na ingestão e retrieval
                           (estado validado: mxbai-embed-large-v1)

Opcionais no .env (recomendadas para respostas reais do assistente no Streamlit):

  FLOWISE_CHATFLOW_ID — ID do flow no Flowise (Chatflow ou AgentFlow), usado em
                        POST .../api/v1/prediction/{id}. Se estiver vazio, a UI
                        funciona em modo demonstração (sem chamar o fluxo com ID).
  FLOWISE_API_KEY     — Chave de API do Flowise, se o servidor estiver configurado para
                        exigir autenticação (cabeçalho Authorization: Bearer ...).
  ELISA_HOST_XLSX_DIR — (Só Docker / opcional) Caminho **no host** (Windows/Linux) da pasta
                        com `.xlsx`. O `docker-compose.yml` monta essa pasta em `/data/elisa`
                        no contêiner Streamlit. Se não definir, usa-se por padrão
                        `./Example/results/ELISA` (relativo à pasta do `docker-compose.yml`;
                        o Docker cria a pasta no host se ainda não existir).
  ELISA_XLSX_DIR      — (Execução local sem Docker) Caminho absoluto à pasta com `.xlsx`.
                        Dentro do Docker **não** use caminhos Windows aqui: o Compose define
                        `ELISA_XLSX_DIR=/data/elisa` no serviço; os arquivos vêm do volume
                        montado a partir de `ELISA_HOST_XLSX_DIR` ou da pasta padrão.
                        Se vazio e sem Docker, a app tenta `Example/results/ELISA` no repositório.

Dentro do contêiner Streamlit (já definidas no compose; não precisa repetir no .env):

  FLOWISE_BASE_URL     — URL interna para chamadas HTTP entre contêineres
                         (http://flowise:3000)
  FLOWISE_PUBLIC_PORT  — só para mensagens na UI; precisa coincidir com o mapeamento
                         no host (o Compose repassa o valor de FLOWISE_PORT do .env)
  FLOWISE_CHATFLOW_ID  — repete o valor do .env do host (pode ficar vazio)
  FLOWISE_API_KEY      — repete o valor do .env do host (pode ficar vazio)
  CHROMA_HOST          — host do Chroma na rede Docker (chroma)
  CHROMA_PORT          — porta do Chroma na rede Docker (8000)
  CHROMA_COLLECTION    — coleção vetorial padrão para o RAG
  LMSTUDIO_BASE_URL    — URL do LM Studio para embeddings/chat OpenAI-compatible
  LMSTUDIO_EMBEDDING_MODEL — nome do modelo de embeddings no LM Studio
  LAB_CHAT_DATA_DIR    — diretório onde é gravado o histórico de conversas (/app/data),
                         persistido pelo volume streamlit_chat_data
  ELISA_XLSX_DIR      — fixo no contêiner como `/data/elisa` (definido no compose; não passe
                         caminhos `D:\...` do Windows). A origem dos arquivos é o bind
                         `${ELISA_HOST_XLSX_DIR:-./Example/results/ELISA}:/data/elisa`

Execução local do Streamlit (fora do Docker), na pasta apps/streamlit:

  • Opcional: LAB_CHAT_DATA_DIR — se não definida, o histórico grava-se em apps/streamlit/data/
    (pasta ignorada pelo Git; criada automaticamente).
  • FLOWISE_BASE_URL — por exemplo http://localhost:3000 se o Flowise estiver no host.
  • FLOWISE_CHATFLOW_ID / FLOWISE_API_KEY — mesma semântica que no compose.
  • ELISA_XLSX_DIR — caminho absoluto da pasta com `.xlsx` (ou vazio para tentativa em
    `Example/results/ELISA`). No Docker use `ELISA_HOST_XLSX_DIR` no `.env` (ver seção de variáveis).

Comportamento técnico
---------------------
  • O Flowise escuta na porta 3000 dentro da rede Docker; o mapeamento para o
    host é ${FLOWISE_PORT:-3000}:3000.
  • O Chroma escuta na porta 8000 dentro da rede Docker; o mapeamento para o
    host é ${CHROMA_PORT:-8000}:8000.
  • Healthcheck do Flowise: GET http://127.0.0.1:3000/api/v1/ping (curl dentro
    da imagem). O Streamlit depende de service_healthy para não iniciar antes
    do Flowise estar pronto.
  • Dados do Flowise (base SQLite e arquivos sob DATABASE_PATH) persistem no
    volume Docker ai_lab_manager_flowise_data montado em /root/.flowise.
  • Com o ID do flow definido no ambiente (ou em secrets), o Streamlit envia cada
    mensagem ao Flowise via HTTP POST em /api/v1/prediction/<id>, com corpo JSON que
    inclui "question", "sessionId" (ID da conversa no Streamlit, para memória por conversa
    no Flowise quando o fluxo o suportar) e "streaming": true. O Flowise devolve eventos
    SSE (`message:` + linha `data:` com JSON contendo `event` e `data`; tokens em
    `event: "token"`). A UI usa `st.write_stream` para mostrar o texto à medida que chega.
    Se a resposta vier como JSON único (sem SSE) ou se o fluxo não emitir tokens, o
    cliente faz fallback para uma predição síncrona sem streaming, para evitar tela
    em branco. Sem ID configurado, não há chamada real ao endpoint: resposta de
    demonstração em fatias apenas na UI.
  • Para RAG: o Flowise consulta o Chroma (vector store) e usa embeddings servidos
    pelo LM Studio via API OpenAI-compatible.
  • Histórico de conversas do Streamlit: arquivo JSON chat_sessions.json sob
    LAB_CHAT_DATA_DIR (no Docker: /app/data, volume ai_lab_manager_streamlit_chat_data).

Interface Streamlit (funcional)
-------------------------------
  • Abas principais: "Assistente" (chat) e "Dados ELISA (DuckDB)" (dados em Excel).
  • Barra lateral: nova conversa, lista de conversas anteriores, exportar conversa (.docx),
    estado da conexão com o Flowise, remoção da conversa atual (se existir mais do que uma).
  • Assistente: thread em um contêiner com altura fixa e rolagem; resposta do modelo em
    streaming quando o Flowise envia tokens; histórico gravado só após a resposta completa.
  • ELISA (DuckDB): carrega `.xlsx` da pasta configurada, pré-visualização de tabelas,
    editor SQL (DuckDB), resultado com scroll e formatação de colunas, botão de descarga
    CSV (UTF-8 com BOM) e gráficos de barras opcionais em expanders quando existir coluna
    numérica. Botão "Recarregar Excel" limpa o cache em memória.
  • Tema (theme.py): cores claras P&D; `padding-top` na área principal dimensionado para
    o cabeçalho nativo do Streamlit não sobrepor as abas; ajustes para tela estreita.
  • Dependências Python: requests, python-docx, duckdb, pandas, openpyxl
    (ver apps/streamlit/requirements.txt).

Estrutura relevante do repositório
----------------------------------
  docker-compose.yml      — definição dos serviços
  .env.example            — modelo de variáveis
  apps/flowise/
    RAG_MVP_SETUP.md      — bootstrap do RAG no Flowise com Chroma + LM Studio
  apps/streamlit/         — código e Dockerfile do Streamlit
    app.py                — aplicação principal (abas chat + ELISA, exportação)
    theme.py              — tema claro P&D (CSS injetado; espaço para cabeçalho Streamlit)
    env_config.py         — leitura de config sensível (ambiente + st.secrets; sem literais)
    chat_sessions.py      — modelo e persistência das conversas (JSON)
    flowise_client.py     — predição síncrona e streaming (SSE Flowise + fallback JSON)
    elisa_ui.py           — aba ELISA (Streamlit + DuckDB)
    elisa_duckdb.py       — carga de Excel em memória e execução SQL
    export_utils.py       — exportação DOCX
    Dockerfile            — copia o diretório apps/streamlit para a imagem (COPY . .)
    requirements.txt
    data/                 — apenas em execução local sem Docker: arquivos de estado
                            (ignorado pelo Git; ver .gitignore)

  packages/ingest/        — scripts de ingestão e validação de retrieval
    chroma_ingest.py      — chunking + embeddings + upsert idempotente no Chroma
    rag_eval.py           — avaliação básica de recall@k em conjunto dourado JSON
    requirements.txt

RAG com Chroma + embeddings (MVP)
---------------------------------
Passo a passo recomendado para execução sem erro:

1) Inicie a stack:

     docker compose up --build -d

2) Verifique a saúde dos serviços:

     docker compose ps

   Resultado esperado: `flowise` e `chroma` com status `healthy`.

3) Abra o Flowise e configure o Document Store (RAG):

   • Loader:
     - Docx File Loader
     - criar dois loaders: um para documentos de sensibilização e outro para otimização

   • Text Splitter:
     - Token Text Splitter
     - encoding: gpt2
     - chunk size: 300
     - chunk overlap: 100

   • Embeddings (LM Studio):
     - provider OpenAI-compatible apontando para LM Studio
     - model: `mxbai-embed-large-v1`
     - dimensions: 1024
     - batch size: 20
     - timeout: 360

   • Vector Store (Chroma):
     - URL: `http://chroma:8000`
     - collection: defina um nome explícito por projeto (ex.: `ProjetoELISA_1024`)
     - top-k: 5

4) Execute o upsert no Document Store.

5) (Opcional) Valide retrieval com scripts locais:

     pip install -r packages/ingest/requirements.txt
     python packages/ingest/rag_eval.py --golden-set .\data\golden_set.json --top-k 5

O script de ingestão local usa metadados mínimos por chunk:
  chunk_id, doc_id, source_uri, lang, content_hash, ingested_at, project
e aplica idempotência por combinação estável de chunk_id + content_hash.

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
      requirements.txt, app.py e os módulos Python referenciados na seção de estrutura.

  • Chat em modo demonstração ou sem resposta do fluxo:
      Confirme FLOWISE_CHATFLOW_ID no .env (ID correto do Chatflow/AgentFlow no Flowise) e que o
      fluxo está publicado/ativo. Em caso de 401/403, configure FLOWISE_API_KEY conforme
      a instância do Flowise.
  • Streaming sem texto visível ou resposta só no fim:
      Confirme que o Flowise e o nó de LLM no fluxo suportam streaming. Proxies que
      bufferizam o corpo podem atrasar os tokens; o cliente tenta fallback síncrono se
      não receber eventos `token` no SSE.
  • Aba ELISA sem dados ou pasta inválida:
      Fora do Docker: `ELISA_XLSX_DIR` com caminho absoluto no sistema onde corre o Streamlit
      (sem aspas extra no `.env`). Dentro do Docker: caminhos `D:\...` não existem no Linux
      do contêiner — use `ELISA_HOST_XLSX_DIR` com a pasta no Windows e confirme o bind
      `...:/data/elisa` no `docker-compose.yml`; o contêiner lê sempre `/data/elisa`.
  • Abas "Assistente" / "ELISA" parcialmente cobertas pelo menu do Streamlit:
      O tema reserva espaço no topo da área principal; se após atualizar o Streamlit o
      problema voltar, ajuste o `padding-top` em `apps/streamlit/theme.py`.

  • Upsert no Flowise falha com "ChromaConnectionError":
      Verifique a URL do Chroma no Vector Store do Flowise.
      Em Docker, use `http://chroma:8000` (não use `127.0.0.1` dentro do Flowise).
      Se a coleção estiver com dimensionalidade antiga (ex.: 768), crie nova coleção
      para 1024 dimensões (ex.: `ProjetoELISA_1024`) e execute novo upsert.

  • Erro de dimensionalidade no Chroma (768 vs 1024):
      A dimensionalidade da coleção é fixada no primeiro insert.
      Para mudar de 768 para 1024, use um novo nome de coleção ou apague a coleção antiga
      e faça nova ingestão de todos os documentos com o modelo atual.

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

  • Reconstruir só o Streamlit depois de mudar o código ou variáveis embutidas na imagem:
      docker compose build --no-cache streamlit
      docker compose up -d streamlit
      (O Compose repassa o `.env` do host ao contêiner em cada `up`; variáveis só no `.env`
      não exigem rebuild, mas alterações em `apps/streamlit/*.py` exigem rebuild da imagem.)

Notas para evolução (fora deste compose)
----------------------------------------
  • LM Studio no host (modelos locais): os contêineres acessam o host em geral
    via host.docker.internal no Windows; isso será documentado quando integrar
    modelos locais diretamente neste compose.
  • Ideias típicas: anexos no chat, mais visualizações na aba de dados, cancelamento
    de pedido em curso (abort do streaming).

================================================================================
  Fim do README
================================================================================
