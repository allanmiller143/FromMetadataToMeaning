# Instala e acesso ao banco Magento 2 (MySQL 8.0)

Este documento descreve o procedimento realizado para instalar e configurar o banco de dados `magento2` em MySQL Server 8.0 no Windows, conforme executado em 17/09/2026.

---

## 1. Instala e configuração do MySQL Server 8.0

1. Baixar o **MySQL Installer for Windows** em:  
   https://dev.mysql.com/downloads/installer/

2. Executar o instalador e escolher a opção **Server only** (ou **Full**, se preferir).

3. Durante a instalação:
   - Definir a **senha do usuário `root`** (anotar em local seguro).
   - Manter a porta padrão **3306**.
   - Concluir a instalação e garantir que o serviço **MySQL80** esteja rodando.

4. Verificar se o MySQL está acessando pelo terminal:

   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
   ```

   Digitar a senha definida na instalação.

---

## 2. Importar o dump SQL do Magento 2

1. Ter em mãos o arquivo SQL com o dump do banco (ex.: `magento2.sql`).

2. Abrir o PowerShell na pasta onde está o arquivo SQL.

3. Executar o comando de import:

   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p < magento2.sql
   ```

4. Digitar a senha do `root` e aguardar a import.

   - O comando cria o banco `magento2` e todas as tabelas e dados contidos no dump.

---

## 3. Verificar o banco e as tabelas

1. Listar os bancos:

   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "SHOW DATABASES;"
   ```

2. Listar as tabelas do banco `magento2`:

   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "USE magento2; SHOW TABLES;"
   ```

   - Resultado esperado: listagem de **295 tabelas** (no caso do Magento 2).

---

## 4. Acessar o banco via Python (SQLAlchemy)

1. Criar um arquivo `.env` na raiz do projeto com as credenciais:

   ```env
   MYSQL_USER=root
   MYSQL_PASS=SUA_SENHA_DO_ROOT
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_DB=magento2
   ```

2. Instalar as dependncias Python (se ainda não tiver):

   ```bash
   pip install sqlalchemy pymysql python-dotenv pandas
   ```

3. Executar o script de extrao de metadados:

   ```bash
   python seu_script_de_extracao.py
   ```

   - O script vai conectar no banco, percorrer as 295 tabelas e gerar os arquivos de metadados em `data/magento2/step1_output/`.

---

## 5. Localização física dos arquivos do banco

Por padrão, no Windows, os arquivos do banco ficam em:

- `C:\ProgramData\MySQL\MySQL Server 8.0\Data\magento2\`

Dentro dessa pasta esto os arquivos `.ibd` (dados das tabelas) e demais arquivos do MySQL.

---

## 6. Resumo das credenciais usadas

- **Host:** `localhost`  
- **Porta:** `3306`  
- **Usuáµ¡rio:** `root`  
- **Senha:** (definida na instalação do MySQL)  
- **Banco:** `magento2`  
- **Total de tabelas:** 295  

---

## 7. Referncias

- MySQL Installer for Windows: https://dev.mysql.com/downloads/installer/  
- Documentao oficial do MySQL 8.0: https://dev.mysql.com/doc/refman/8.0/en/  
- Magento 2 Database Documentation: https://developer.adobe.com/commerce/frontend-core/guide/db/