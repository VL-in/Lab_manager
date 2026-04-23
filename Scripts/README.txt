================================================================================
  AI_lab_manager — assistente de laboratório (protótipo Docker)
================================================================================

Visão geral
-----------
Stack local com Docker Compose:
  • Flowise  — orquestração de fluxos / agentes (UI no host: veja a porta em FLOWISE_PORT)
  • Streamlit — interface web do laboratório (UI no host: veja a porta em STREAMLIT_PORT)

Nome do projeto Compose: ai_lab_manager.
Containers: ai_lab_manager_flowise, ai_lab_manager_streamlit.
Volume nomeado para dados do Flowise: ai_lab_manager_flowise_data.

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

5) Parar os contêineres (mantém o volume com dados do Flowise):

     docker compose down

   Para parar e apagar também o volume persistente do Flowise (apaga fluxos
   salvos no volume):

     docker compose down -v

Variáveis de ambiente (.env)
----------------------------
Definidas em .env.example — copie para .env na mesma pasta que o docker-compose.yml.

  STREAMLIT_PORT  — porta publicada no host para o Streamlit (padrão: 8501)
  FLOWISE_PORT    — porta publicada no host para o Flowise (padrão: 3000; use outra,
                    ex. 3001, só se a 3000 do host estiver ocupada)

Dentro do contêiner Streamlit (já definidas no compose; não precisa repetir no .env):

  FLOWISE_BASE_URL     — URL interna para chamadas HTTP entre contêineres
                         (http://flowise:3000)
  FLOWISE_PUBLIC_PORT  — só para mensagens na UI; precisa coincidir com o mapeamento
                         no host (o Compose repassa o valor de FLOWISE_PORT do .env)

Comportamento técnico
---------------------
  • O Flowise escuta na porta 3000 dentro da rede Docker; o mapeamento para o
    host é ${FLOWISE_PORT:-3000}:3000.
  • Healthcheck do Flowise: GET http://127.0.0.1:3000/api/v1/ping (curl dentro
    da imagem). O Streamlit depende de service_healthy para não iniciar antes
    do Flowise estar pronto.
  • Dados do Flowise (base SQLite e arquivos sob DATABASE_PATH) persistem no
    volume Docker ai_lab_manager_flowise_data montado em /root/.flowise.

Estrutura relevante do repositório
----------------------------------
  docker-compose.yml      — definição dos serviços
  .env.example            — modelo de variáveis
  apps/streamlit/         — código e Dockerfile do Streamlit
    app.py                — aplicação Streamlit (título AI_lab_manager)
    Dockerfile
    requirements.txt

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
      requirements.txt e app.py.

  • Ver estado dos serviços:
      docker compose ps

  • Reconstruir só o Streamlit depois de mudar o código:
      docker compose build --no-cache streamlit; docker compose up -d

Notas para evolução (fora deste compose)
----------------------------------------
  • LM Studio no host (modelos locais): os contêineres acessam o host em geral
    via host.docker.internal no Windows; isso será documentado quando integrar
    chat/API no Streamlit ou no Flowise.

================================================================================
  Fim do README
================================================================================
