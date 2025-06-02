# LexiChess MVP - Task Breakdown

## Phase 1: LLM Tournament System, Hallucination Tracking, Time Controls, SQLite Logging

### I. Project Setup & Core Dependencies
---
**Task 1.1: Initialize Project Directory Structure**
* **Description**: Create the base folder structure for the LexiChess project as outlined in `docs/file_structure.md`.
* **Files to Create/Modify**:
    * `lexichess/` (root folder)
    * `lexichess/Notebooks/`
    * `lexichess/Sandbox/`
    * `lexichess/src/`
    * `lexichess/src/chess/`
    * `lexichess/src/llm/`
    * `lexichess/src/tutoring/` (can be empty for MVP)
    * `lexichess/src/api/` (can be empty for MVP)
    * `lexichess/src/database/`
    * `lexichess/frontend/` (can be empty for MVP)
    * `lexichess/docs/`
    * `lexichess/docs/diagrams/`
    * `lexichess/tests/`
    * `lexichess/tests/chess/`
    * `lexichess/tests/llm/`
    * `lexichess/tests/database/`
    * `lexichess/scripts/`
* **Start**: No prior LexiChess code.
* **End**: The specified directory structure exists on the file system.
* **Test**: Manually verify that all listed directories have been created.

---
**Task 1.2: Initialize `pyproject.toml`**
* **Description**: Create a `pyproject.toml` file and define basic project metadata and the `python-chess` dependency.
* **Files to Create/Modify**: `lexichess/pyproject.toml`
* **Content Example (for Poetry)**:
    ```toml
    [tool.poetry]
    name = "lexichess"
    version = "0.1.0"
    description = "A platform for LLM chess tournaments, tutoring, and research."
    authors = ["Your Name <you@example.com>"]
    license = "MIT"
    readme = "README.md"

    [tool.poetry.dependencies]
    python = "^3.10"
    python-chess = "^1.99" # Or latest stable version

    [tool.poetry.dev-dependencies]
    pytest = "^7.0" # Or latest stable version
    ```
* **Start**: `pyproject.toml` does not exist.
* **End**: `pyproject.toml` exists with initial configuration and `python-chess` dependency.
* **Test**: Run `poetry install` (or equivalent for your chosen package manager) to ensure the file is valid and `python-chess` can be installed. `poetry check` should pass.

---
**Task 1.3: Initialize Git Repository and `.gitignore`**
* **Description**: Initialize a Git repository in the `lexichess` root folder and create a basic `.gitignore` file.
* **Files to Create/Modify**: `lexichess/.gitignore`
* **`.gitignore` Content Example**:
    ```
    # Python
    __pycache__/
    *.pyc
    *.pyo
    *.pyd
    .Python
    env/
    venv/
    *.egg-info/
    dist/
    build/

    # IDEs
    .idea/
    .vscode/

    # SQLite
    *.db
    *.sqlite3

    # Other
    .DS_Store
    ```
* **Start**: No Git repository or `.gitignore` file.
* **End**: A Git repository is initialized, and `.gitignore` is created and committed.
* **Test**: Run `git status`. It should show a clean working tree after committing `.gitignore` and `pyproject.toml`.

---
### II. Database Module (`src/database/`)
---
**Task 2.1: Define Games Table Schema**
* **Description**: Define the SQLAlchemy model or SQL `CREATE TABLE` statement for the `games` table. This table will store information about each chess game.
* **Files to Create/Modify**: `lexichess/src/database/schema.py`
* **Details**:
    * `games` table columns:
        * `id` (Integer, Primary Key, Auto-increment)
        * `start_time` (DateTime, Default: current timestamp)
        * `white_player_name` (String)
        * `black_player_name` (String)
        * `white_player_type` (String, e.g., 'llm', 'stockfish', 'human')
        * `black_player_type` (String, e.g., 'llm', 'stockfish', 'human')
        * `status` (String, e.g., 'ongoing', 'completed', 'aborted')
        * `result` (String, e.g., '1-0', '0-1', '1/2-1/2', 'timeout_white', 'timeout_black', 'invalid_move_white', 'invalid_move_black')
        * `end_time` (DateTime, Nullable)
        * `time_control` (String, e.g., '5+3')
* **Start**: `schema.py` is empty or does not exist.
* **End**: `schema.py` contains the definition for the `games` table.
* **Test**: Code review of `schema.py` to ensure all specified fields and types are present.

---
**Task 2.2: Implement Database Connection Utility**
* **Description**: Create a utility function to establish a connection to the SQLite database and return a session/connection object.
* **Files to Create/Modify**: `lexichess/src/database/queries.py`
* **Details**:
    * Function should accept a database file path (e.g., `lexichess.db`).
    * Use SQLAlchemy or the standard `sqlite3` module.
* **Start**: `queries.py` is empty or does not exist.
* **End**: `queries.py` contains a function to connect to the SQLite database.
* **Test**: Write a simple test (e.g., in `tests/database/test_queries.py` or a temporary script) that calls the connection function and confirms a connection object is returned without errors using a temporary in-memory database.

---
**Task 2.3: Implement Table Creation Function**
* **Description**: Create a function that uses the schema definitions from `schema.py` to create all defined tables in the database.
* **Files to Create/Modify**: `lexichess/src/database/queries.py` (or a new `setup.py` in `src/database/`)
* **Details**:
    * This function will use the SQLAlchemy models' `metadata.create_all(engine)` or execute `CREATE TABLE` SQL statements.
* **Start**: Table creation logic does not exist.
* **End**: A function is available to create database tables.
* **Test**: Call this function. Verify that the `games` table is created in a test SQLite database file by inspecting the DB with a SQLite browser or programmatically.

---
**Task 2.4: Define Moves Table Schema**
* **Description**: Define the schema for the `moves` table. This table will log every move made in a game.
* **Files to Create/Modify**: `lexichess/src/database/schema.py`
* **Details**:
    * `moves` table columns:
        * `id` (Integer, Primary Key, Auto-increment)
        * `game_id` (Integer, Foreign Key referencing `games.id`)
        * `move_number` (Integer)
        * `player_color` (String, 'white' or 'black')
        * `san_move` (String, e.g., 'e4', 'Nf3')
        * `fen_before_move` (String)
        * `fen_after_move` (String)
        * `timestamp` (DateTime, Default: current timestamp)
        * `time_taken_seconds` (Float, Nullable)
        * `is_valid_chess_move` (Boolean)
* **Start**: `moves` table schema does not exist in `schema.py`.
* **End**: `schema.py` is updated with the definition for the `moves` table.
* **Test**: Update the table creation test (from Task 2.3) to verify the `moves` table is also created correctly.

---
**Task 2.5: Define Hallucinations Table Schema**
* **Description**: Define the schema for the `hallucinations` table. This table logs instances where an LLM provides an invalid move or makes a reasoning error detectable by the system.
* **Files to Create/Modify**: `lexichess/src/database/schema.py`
* **Details**:
    * `hallucinations` table columns:
        * `id` (Integer, Primary Key, Auto-increment)
        * `game_id` (Integer, Foreign Key referencing `games.id`)
        * `move_id` (Integer, Foreign Key referencing `moves.id`, Nullable if hallucination is not tied to a specific move attempt that got recorded)
        * `llm_player_name` (String)
        * `attempted_move_or_text` (String, the problematic output from LLM)
        * `reason_type` (String, e.g., 'invalid_san_format', 'illegal_move', 'non_move_response', 'failed_to_parse_move')
        * `description` (Text, optional, for more details)
        * `timestamp` (DateTime, Default: current timestamp)
* **Start**: `hallucinations` table schema does not exist in `schema.py`.
* **End**: `schema.py` is updated with the definition for the `hallucinations` table.
* **Test**: Update the table creation test (from Task 2.3) to verify the `hallucinations` table is also created correctly.

---
**Task 2.6: Define LLM Conversations Table Schema**
* **Description**: Define the schema for the `llm_conversations` table. This table logs the raw prompts sent to LLMs and their full responses.
* **Files to Create/Modify**: `lexichess/src/database/schema.py`
* **Details**:
    * `llm_conversations` table columns:
        * `id` (Integer, Primary Key, Auto-increment)
        * `game_id` (Integer, Foreign Key referencing `games.id`)
        * `move_id` (Integer, Foreign Key referencing `moves.id`, Nullable, links to the move resulting from this convo)
        * `llm_player_name` (String)
        * `prompt_text` (Text)
        * `raw_response_text` (Text)
        * `timestamp` (DateTime, Default: current timestamp)
* **Start**: `llm_conversations` table schema does not exist in `schema.py`.
* **End**: `schema.py` is updated with the definition for the `llm_conversations` table.
* **Test**: Update the table creation test (from Task 2.3) to verify the `llm_conversations` table is also created correctly. Create `scripts/setup_db.py` that calls the table creation function. Running `python scripts/setup_db.py` should create a `lexichess.db` file with all four tables.

---
**Task 2.7: Implement Function to Log a New Game**
* **Description**: Create a function in `queries.py` to insert a new record into the `games` table.
* **Files to Create/Modify**: `lexichess/src/database/queries.py`
* **Details**:
    * Function should accept parameters like `white_player_name`, `black_player_name`, `white_player_type`, `black_player_type`, `time_control`.
    * It should set `status` to 'ongoing' and `start_time` to current time.
    * It should return the ID of the newly created game.
* **Start**: No function to log a new game.
* **End**: `log_new_game(db_session, ...)` function exists and works.
* **Test**: Write a unit test in `tests/database/test_queries.py` that calls `log_new_game` and verifies that a new record is correctly inserted into the `games` table and the game ID is returned.

---
**Task 2.8: Implement Function to Log a Move**
* **Description**: Create a function in `queries.py` to insert a new record into the `moves` table.
* **Files to Create/Modify**: `lexichess/src/database/queries.py`
* **Details**:
    * Function should accept `game_id`, `move_number`, `player_color`, `san_move`, `fen_before_move`, `fen_after_move`, `time_taken_seconds`, `is_valid_chess_move`.
    * It should return the ID of the newly logged move.
* **Start**: No function to log a move.
* **End**: `log_move(db_session, ...)` function exists and works.
* **Test**: Write a unit test in `tests/database/test_queries.py`. First, log a dummy game to get a `game_id`. Then, call `log_move` and verify the record is correctly inserted into the `moves` table with the correct `game_id`.

---
**Task 2.9: Implement Function to Log a Hallucination**
* **Description**: Create a function in `queries.py` to insert a new record into the `hallucinations` table.
* **Files to Create/Modify**: `lexichess/src/database/queries.py`
* **Details**:
    * Function should accept `game_id`, `move_id` (optional), `llm_player_name`, `attempted_move_or_text`, `reason_type`, `description` (optional).
* **Start**: No function to log a hallucination.
* **End**: `log_hallucination(db_session, ...)` function exists and works.
* **Test**: Write a unit test in `tests/database/test_queries.py`. Log a dummy game, (optionally a dummy move), then call `log_hallucination` and verify the record is correctly inserted.

---
**Task 2.10: Implement Function to Log an LLM Conversation**
* **Description**: Create a function in `queries.py` to insert a new record into the `llm_conversations` table.
* **Files to Create/Modify**: `lexichess/src/database/queries.py`
* **Details**:
    * Function should accept `game_id`, `move_id` (optional), `llm_player_name`, `prompt_text`, `raw_response_text`.
* **Start**: No function to log an LLM conversation.
* **End**: `log_llm_conversation(db_session, ...)` function exists and works.
* **Test**: Write a unit test in `tests/database/test_queries.py`. Log a dummy game, then call `log_llm_conversation` and verify the record is correctly inserted.

---
**Task 2.11: Implement Function to Update Game Result**
* **Description**: Create a function in `queries.py` to update an existing game record in the `games` table with the game's outcome.
* **Files to Create/Modify**: `lexichess/src/database/queries.py`
* **Details**:
    * Function should accept `game_id`, `status` (e.g., 'completed'), `result` (e.g., '1-0'), and `end_time`.
* **Start**: No function to update game result.
* **End**: `update_game_result(db_session, game_id, status, result, end_time)` function exists and works.
* **Test**: Write a unit test. Log a new game, then call `update_game_result` and verify the game record is updated correctly.

---
### III. Chess Logic Module (`src/chess/`)
---
**Task 3.1: Create `ChessBoard` Wrapper Class in `board.py`**
* **Description**: Create a class `ChessBoard` in `src/chess/board.py` that wraps `python-chess.Board`.
* **Files to Create/Modify**: `lexichess/src/chess/board.py`, `lexichess/src/chess/__init__.py` (if it doesn't exist)
* **Details**:
    * The constructor `__init__` should initialize an internal `python-chess.Board` instance.
* **Start**: `board.py` does not exist or is empty.
* **End**: `ChessBoard` class exists with an initialized `python-chess.Board`.
* **Test**: Create a unit test in `tests/chess/test_board.py` that instantiates `ChessBoard` and verifies that `self.board` is an instance of `chess.Board`.

---
**Task 3.2: Implement `make_move` Method in `ChessBoard`**
* **Description**: Add a method `make_move(self, san_move)` to `ChessBoard` that attempts to make a move using SAN notation.
* **Files to Create/Modify**: `lexichess/src/chess/board.py`
* **Details**:
    * Uses `self.board.push_san(san_move)`.
    * Should handle potential exceptions from `push_san` (e.g., `ValueError` for illegal or ambiguous moves) and return `True` for success, `False` for failure.
* **Start**: `ChessBoard` class exists but lacks `make_move`.
* **End**: `make_move` method is implemented and handles basic success/failure.
* **Test**: In `tests/chess/test_board.py`, test `make_move` with a valid SAN move (e.g., "e4" from starting position) and assert it returns `True`. Test with an invalid SAN move (e.g., "e5" from starting position) and assert it returns `False` and the board state remains unchanged.

---
**Task 3.3: Implement `is_move_legal` Method in `ChessBoard`**
* **Description**: Add a method `is_move_legal(self, san_move)` to `ChessBoard` to check if a move in SAN is legal without making it.
* **Files to Create/Modify**: `lexichess/src/chess/board.py`
* **Details**:
    * This method should try to parse the move (`self.board.parse_san(san_move)`) and see if it's in `self.board.legal_moves`.
    * Return `True` if legal, `False` otherwise.
* **Start**: `ChessBoard` class exists but lacks `is_move_legal`.
* **End**: `is_move_legal` method is implemented.
* **Test**: In `tests/chess/test_board.py`, test `is_move_legal` with "e4" (should be true) and "e5" (should be false) from the starting position.

---
**Task 3.4: Implement Board State Methods in `ChessBoard`**
* **Description**: Add methods to `ChessBoard` to get FEN, check game over conditions, and get the outcome.
* **Files to Create/Modify**: `lexichess/src/chess/board.py`
* **Details**:
    * `get_fen(self)`: Returns `self.board.fen()`.
    * `is_game_over(self)`: Returns `self.board.is_game_over()`.
    * `get_outcome(self)`: Returns `self.board.outcome()` if the game is over, otherwise `None`. This will give information on winner and termination type (checkmate, stalemate, etc.).
    * `get_legal_moves_san(self)`: Returns a list of legal moves in SAN format. (Iterate `self.board.legal_moves` and use `self.board.san(move)`).
* **Start**: `ChessBoard` methods for FEN, game over, outcome, and legal moves SAN list are missing.
* **End**: These methods are implemented.
* **Test**: In `tests/chess/test_board.py`:
    * Verify `get_fen()` returns the starting FEN for a new board.
    * Verify `is_game_over()` is `False` for a new board.
    * Verify `get_outcome()` is `None` for a new board.
    * Set up a checkmate position (e.g., Fool's Mate), verify `is_game_over()` is `True` and `get_outcome()` returns the correct winner and termination.
    * Verify `get_legal_moves_san()` returns a non-empty list of strings for the starting position (e.g., includes "e4", "d4", etc.).

---
**Task 3.5: Create `TimeControl` Class**
* **Description**: Implement a basic `TimeControl` class in `src/chess/time_control.py`.
* **Files to Create/Modify**: `lexichess/src/chess/time_control.py`, `lexichess/src/chess/__init__.py`
* **Details**:
    * Constructor `__init__(self, initial_time_seconds, increment_seconds)`:
        * Stores `initial_time_seconds` and `increment_seconds`.
        * Initializes `time_left_white` and `time_left_black` to `initial_time_seconds`.
        * Stores the time of the last move for calculating duration.
    * `start_turn(self, player_color)`: Records the current time as the start of the turn for `player_color`.
    * `end_turn(self, player_color)`: Calculates time taken for the turn. Deducts time taken from `player_color`'s remaining time. Adds `increment_seconds` to `player_color`'s time. Updates last move time.
    * `get_remaining_time(self, player_color)`: Returns remaining time for `player_color`.
    * `check_timeout(self, player_color)`: Returns `True` if `player_color`'s time is <= 0, else `False`.
* **Start**: `time_control.py` does not exist or is empty.
* **End**: `TimeControl` class with specified methods is implemented.
* **Test**: Create `tests/chess/test_time_control.py`.
    * Test initialization: verify initial times for white and black.
    * Test `start_turn` and `end_turn`: simulate a move taking a few seconds, verify time deduction and increment addition.
    * Test `check_timeout`: manually set a player's time to 0 or negative and verify timeout detection.

---
### IV. LLM Integration - Base (`src/llm/`)
---
**Task 4.1: Create `PromptGenerator` Class**
* **Description**: Create a `PromptGenerator` class in `src/llm/prompt.py`.
* **Files to Create/Modify**: `lexichess/src/llm/prompt.py`, `lexichess/src/llm/__init__.py`
* **Details**:
    * Method `get_move_prompt(self, board_fen, player_color, legal_moves_san_list, opponent_last_move_san=None)`:
        * Constructs a string prompt asking the LLM to choose its next move.
        * The prompt should include: current board FEN, whose turn it is (player_color), a list of legal moves in SAN format. Optionally, the opponent's last move.
        * Example: "You are playing chess as {player_color}. The current board FEN is: {board_fen}. Your legal moves are: {', '.join(legal_moves_san_list)}. Choose your next move in Standard Algebraic Notation (SAN)."
* **Start**: `prompt.py` does not exist or is empty.
* **End**: `PromptGenerator` class with `get_move_prompt` method is implemented.
* **Test**: Create `tests/llm/test_prompt.py`. Call `get_move_prompt` with sample FEN, color, and legal moves list. Verify the output string contains all the provided information in a coherent structure.

---
### V. Stockfish Integration
---
**Task 5.1: Install Stockfish Python Package**
* **Description**: Add the `stockfish` Python package to `pyproject.toml` and install it.
* **Files to Create/Modify**: `lexichess/pyproject.toml`
* **Details**: Add `stockfish = "^<latest_version>"` to dependencies.
* **Start**: `stockfish` package not in dependencies.
* **End**: `stockfish` package is listed in `pyproject.toml` and installed in the environment.
* **Test**: Run `poetry install` (or equivalent). Try `import stockfish` in a Python interpreter. Ensure Stockfish engine binary is downloaded/accessible by the package (it often handles this automatically or requires a path).

---
**Task 5.2: Create `StockfishPlayer` Class**
* **Description**: Implement a `StockfishPlayer` class in `src/chess/engine_player.py` to interface with the Stockfish engine.
* **Files to Create/Modify**: `lexichess/src/chess/engine_player.py`, `lexichess/src/chess/__init__.py`
* **Details**:
    * Constructor `__init__(self, stockfish_path="stockfish", skill_level=10, elo=None)`:
        * Initializes `Stockfish` instance from the `stockfish` package.
        * Sets skill level (`set_skill_level(skill_level)`) or ELO (`set_elo_rating(elo)`) if ELO is provided.
    * Method `get_move(self, fen_string)`:
        * Sets the board position using `self.stockfish.set_fen_position(fen_string)`.
        * Gets the best move using `self.stockfish.get_best_move()`. This usually returns a UCI move.
        * Convert UCI move to SAN. (Requires a `python-chess.Board` instance set to the same FEN: `board.parse_uci(uci_move)` then `board.san(parsed_move)`).
        * Return the move in SAN.
* **Start**: `engine_player.py` does not exist.
* **End**: `StockfishPlayer` class is implemented.
* **Test**: Create `tests/chess/test_engine_player.py`.
    * Instantiate `StockfishPlayer`.
    * Call `get_move` with the starting FEN. Verify it returns a valid SAN move (e.g., "e4", "d4", etc.). Ensure you have Stockfish executable available in PATH or provide the path.

---
### VI. Tournament Manager - Core Game Logic (`src/chess/tournament.py`)
---
**Task 6.1: Define `Player` Data Structure**
* **Description**: Define a simple data structure (e.g., `dataclass` or `namedtuple`) named `Player` to hold player information.
* **Files to Create/Modify**: `lexichess/src/chess/tournament.py` (or a new `player.py` within `src/chess/`)
* **Details**:
    * Attributes: `name` (str), `player_type` (str: 'stockfish', 'llm_api', 'llm_local', 'human'), `client_or_engine` (object: e.g., `StockfishPlayer` instance, or an LLM client instance later).
* **Start**: `Player` structure not defined.
* **End**: `Player` data structure is defined.
* **Test**: Can create instances of `Player`.

---
**Task 6.2: Create `TournamentManager` Class - Basic Structure**
* **Description**: Create the `TournamentManager` class in `src/chess/tournament.py`.
* **Files to Create/Modify**: `lexichess/src/chess/tournament.py`, `lexichess/src/chess/__init__.py`
* **Details**:
    * Constructor `__init__(self, db_session)`: Stores the database session.
    * Method `_get_player_move(self, player, board, time_control)`: Placeholder for now.
    * Method `play_game(self, white_player: Player, black_player: Player, time_control_settings: tuple)`:
        * Initializes a new `ChessBoard`.
        * Initializes `TimeControl` using `time_control_settings` (e.g., `(300, 5)` for 5+3).
        * Logs the new game to the database using `queries.log_new_game`, storing the returned `game_id`.
* **Start**: `tournament.py` has no `TournamentManager` or it's very basic.
* **End**: `TournamentManager` class structure is set up. `play_game` initializes board, time control, and logs the game.
* **Test**: Create `tests/chess/test_tournament.py`. Instantiate `TournamentManager` with a mock DB session. Call `play_game` with two dummy `Player` objects. Verify `log_new_game` on the mock DB session was called correctly and that `ChessBoard` and `TimeControl` were instantiated.

---
**Task 6.3: Implement Game Loop in `play_game` for Stockfish vs. Stockfish**
* **Description**: Flesh out the `play_game` method to run a full game turn by turn between two Stockfish players.
* **Files to Create/Modify**: `lexichess/src/chess/tournament.py`
* **Details within `play_game` loop**:
    1.  Determine current player based on board turn.
    2.  If current player is Stockfish (check `player.player_type`):
        * Call `player.client_or_engine.get_move(current_fen)` to get SAN move.
    3.  Validate the move using `ChessBoard.is_move_legal()`.
        * (For Stockfish, moves should always be legal. Add a contingency if not.)
    4.  If legal:
        * Record FEN before move (`board.get_fen()`).
        * Make the move on `ChessBoard` (`board.make_move(san_move)`).
        * Record FEN after move (`board.get_fen()`).
        * Log the move to DB using `queries.log_move` (include `game_id`, move number, player color, SAN, FENs, time taken (can be 0 for now), `is_valid_chess_move=True`).
        * `time_control.end_turn(current_player_color)` (after `time_control.start_turn` at beginning of player's turn consideration).
    5.  Check for game over (`board.is_game_over()`) or timeout (`time_control.check_timeout()`).
    6.  If game over:
        * Get outcome from `board.get_outcome()` or determine from timeout.
        * Update game result in DB using `queries.update_game_result`.
        * Break loop.
    7.  Switch player and continue loop.
* **Start**: `play_game` only initializes.
* **End**: `play_game` can run a full game between two Stockfish players, logging moves and the final game result.
* **Test**: In `tests/chess/test_tournament.py` (or a dedicated script like `scripts/run_stockfish_game.py`):
    * Set up two `StockfishPlayer` instances.
    * Call `play_game`.
    * Inspect the (test) database: a game should be logged, multiple moves for that game, and a final game result.
    * Verify time was correctly deducted (can be very basic checks for now).

---
**Task 6.4: Integrate `TimeControl` Timing in `play_game`**
* **Description**: Properly integrate `TimeControl.start_turn` and `TimeControl.end_turn` and time taken calculation within the `play_game` loop.
* **Files to Create/Modify**: `lexichess/src/chess/tournament.py`
* **Details**:
    * Before getting a move from a player: `time_control.start_turn(current_player_color)`.
    * After a move is received (and before logging it): `time_control.end_turn(current_player_color)`.
    * The `time_taken_seconds` for `log_move` can be derived from the difference recorded by `end_turn` or `start_turn` and `end_turn` can internally calculate and store this for retrieval.
    * Handle game termination due to timeout: If `time_control.check_timeout(player_color)` is true, the other player wins. Update game result accordingly.
* **Start**: Time control usage is basic or non-existent for calculating actual move times.
* **End**: Time taken for moves is calculated, logged, and timeouts correctly end the game.
* **Test**:
    * Run a Stockfish vs. Stockfish game. Verify `time_taken_seconds` in the `moves` table has plausible (small, non-zero) values.
    * Set up a test with very short time limits for one player in `TimeControl`. Ensure this player times out and the game result reflects this.

---
### VII. LLM Integration - API Client (`src/llm/api_client.py`)
---
**Task 7.1: Create `OpenAIClient` for API-based LLMs (Initial)**
* **Description**: Implement a basic `OpenAIClient` in `src/llm/api_client.py` to connect to OpenAI API.
* **Files to Create/Modify**: `lexichess/src/llm/api_client.py`, `lexichess/src/llm/__init__.py`
* **Details**:
    * Add `openai` package to `pyproject.toml`.
    * Constructor `__init__(self, api_key, model_name="gpt-3.5-turbo")`.
    * Method `get_llm_move_response(self, prompt_text)`:
        * Makes a request to the OpenAI Chat Completions API.
        * Returns the raw text content of the LLM's response.
        * Include basic error handling for API requests (e.g., catch `openai.APIError`).
* **Start**: `api_client.py` does not exist or is empty.
* **End**: `OpenAIClient` can send a prompt to OpenAI and get a raw text response. `openai` is a dependency.
* **Test**: Create `tests/llm/test_api_client.py` (requires an OpenAI API key set as an environment variable for testing).
    * Instantiate `OpenAIClient`.
    * Call `get_llm_move_response` with a simple prompt (e.g., "What is 2+2?").
    * Verify a string response is received and no API errors occur. (Mocking the API call is preferred for automated tests if possible).

---
**Task 7.2: Implement Basic SAN Extraction from LLM Response**
* **Description**: Add a utility function or method (perhaps in `src/llm/prompt.py` or `api_client.py`) to attempt to extract a SAN move from the LLM's raw text response.
* **Files to Create/Modify**: `lexichess/src/llm/prompt.py` (or `api_client.py`)
* **Details**:
    * Function `extract_san_from_response(response_text: str, legal_moves: list[str]) -> str | None`:
        * Simplistic initial approach: Iterate through `legal_moves` and check if any are present as a whole word in `response_text`.
        * More advanced: Use regex to find patterns like "e4", "Nf3", "O-O".
        * Return the first valid SAN found, or `None` if no plausible move is found.
* **Start**: No SAN extraction logic.
* **End**: `extract_san_from_response` function is implemented.
* **Test**: In `tests/llm/test_prompt.py` (or a new test file):
    * Test with various sample LLM responses and lists of legal moves:
        * `"My move is e4."`, `["e4", "d4"]` -> should return `"e4"`.
        * `"I'll play Nf3."`, `["Nf3", "Nc3"]` -> should return `"Nf3"`.
        * `"I think the best option is O-O, what do you think?"`, `["O-O", "Kh1"]` -> should return `"O-O"`.
        * `"The board is complex. I am unsure."`, `["e4", "d4"]` -> should return `None`.
        * `"Let's try Knight to c3."` (if `Nc3` is legal) -> should ideally find `Nc3`. This highlights the need for robustness.

---
### VIII. LLM Integration - Local Client (`src/llm/local_client.py`) (Optional for strict MVP if API is primary)
---
**Task 8.1: Create `OllamaClient` for Local LLMs (Initial)**
* **Description**: Implement `OllamaClient` in `src/llm/local_client.py` to connect to a local Ollama server.
* **Files to Create/Modify**: `lexichess/src/llm/local_client.py`, `lexichess/src/llm/__init__.py`
* **Details**:
    * Add `ollama` package to `pyproject.toml`.
    * Constructor `__init__(self, model_name="llama3")`. (User needs Ollama running with this model).
    * Method `get_llm_move_response(self, prompt_text)`:
        * Uses `ollama.chat` or `ollama.generate` to send the prompt.
        * Returns the raw text content of the LLM's response.
        * Include basic error handling.
* **Start**: `local_client.py` does not exist.
* **End**: `OllamaClient` can send a prompt to a local Ollama model and get a raw text response. `ollama` is a dependency.
* **Test**: Create `tests/llm/test_local_client.py` (requires Ollama running with a model like `llama3`).
    * Instantiate `OllamaClient`.
    * Call `get_llm_move_response` with a simple prompt.
    * Verify a string response is received. (Mocking is good here too).

---
### IX. Integrating LLMs into Tournament & Hallucination Logging
---
**Task 9.1: Modify `TournamentManager._get_player_move` for LLMs**
* **Description**: Implement the logic in `TournamentManager._get_player_move` to handle LLM players (API and Local).
* **Files to Create/Modify**: `lexichess/src/chess/tournament.py`
* **Details**:
    * The method should accept `player: Player`, `board: ChessBoard` (to get FEN and legal moves), `prompt_generator: PromptGenerator`.
    * If `player.player_type` is 'llm_api' or 'llm_local':
        1.  Get current FEN from `board.get_fen()`.
        2.  Get legal moves SAN list from `board.get_legal_moves_san()`.
        3.  Generate prompt using `prompt_generator.get_move_prompt(...)`.
        4.  Call `player.client_or_engine.get_llm_move_response(prompt_text)`.
        5.  Log the prompt and raw response to `llm_conversations` table using `queries.log_llm_conversation` (pass `game_id` from the `play_game` context, `move_id` can be `None` for now or logged after move is confirmed).
        6.  Attempt to extract SAN move from response using `extract_san_from_response(raw_response, legal_moves_san_list)`.
        7.  Return the extracted SAN move (or `None` if extraction fails).
* **Start**: `_get_player_move` is a placeholder.
* **End**: `_get_player_move` can get a response from an LLM and attempt to extract a move. LLM conversation is logged.
* **Test**: In `tests/chess/test_tournament.py`:
    * Mock an LLM client (API or Local) to return a predefined response.
    * Mock `PromptGenerator`. Mock `queries.log_llm_conversation`.
    * Call `_get_player_move` with an LLM player.
    * Verify `get_move_prompt` was called.
    * Verify LLM client's method was called.
    * Verify `log_llm_conversation` was called with correct prompt and response.
    * Verify the returned SAN move matches expectations based on the mocked response and `extract_san_from_response` logic.

---
**Task 9.2: Integrate LLM Moves and Hallucination Logging in `play_game`**
* **Description**: Update `play_game` to use `_get_player_move` for LLMs and handle invalid/unparseable moves as hallucinations.
* **Files to Create/Modify**: `lexichess/src/chess/tournament.py`
* **Details (within `play_game` loop for an LLM player)**:
    1.  Call `san_move = self._get_player_move(current_player_obj, self.board, self.prompt_generator)`. (Need to pass `PromptGenerator` to `TournamentManager` or create it there).
    2.  If `san_move` is `None` (LLM failed to provide a parseable move):
        * Log to `hallucinations` table using `queries.log_hallucination` (reason: 'failed_to_parse_move' or 'non_move_response', include raw LLM text).
        * Game ends, opponent wins by 'invalid_move_{color}'. Update DB. Break loop.
    3.  If `san_move` is not `None`, try to validate it with `self.board.is_move_legal(san_move)`.
    4.  If `is_move_legal` is `False`:
        * Log to `hallucinations` table (reason: 'illegal_chess_move', include `san_move`).
        * Log the attempted move to `moves` table with `is_valid_chess_move=False`. Link `hallucination` to this `move_id`.
        * Game ends, opponent wins by 'invalid_move_{color}'. Update DB. Break loop.
    5.  If move is legal and valid:
        * Proceed as with Stockfish: log move (now with `is_valid_chess_move=True`), make move on board, handle time, check game over.
        * Ensure the `move_id` from `log_move` is available to be linked in `llm_conversations` if a separate update call is needed for that.
* **Start**: `play_game` only handles Stockfish or has basic LLM placeholders.
* **End**: `play_game` can manage a game with an LLM player, attempts to get its move, logs conversations, logs hallucinations for unparseable or illegal moves, and ends the game appropriately.
* **Test**:
    * Test scenario where LLM (mocked) returns unparseable text: Verify hallucination is logged, game ends.
    * Test scenario where LLM (mocked) returns an illegal SAN move: Verify hallucination and invalid move are logged, game ends.
    * Test scenario where LLM (mocked) returns a valid SAN move: Verify game proceeds, move and conversation are logged.

---
### X. Scripting & Basic CLI (`scripts/`)
---
**Task 10.1: Enhance `scripts/setup_db.py`**
* **Description**: Ensure `scripts/setup_db.py` correctly initializes the SQLite database with all defined tables.
* **Files to Create/Modify**: `lexichess/scripts/setup_db.py`
* **Details**:
    * Imports database engine/session setup from `src.database.queries` (or wherever connection is defined).
    * Imports table models/metadata from `src.database.schema`.
    * Calls the function to create all tables (e.g., `Base.metadata.create_all(engine)` if using SQLAlchemy).
* **Start**: `setup_db.py` might be basic or non-existent.
* **End**: Running `python scripts/setup_db.py` creates (or recreates) `lexichess.db` with all tables (`games`, `moves`, `hallucinations`, `llm_conversations`).
* **Test**: Delete `lexichess.db` if it exists. Run `python scripts/setup_db.py`. Inspect `lexichess.db` using a SQLite browser to confirm all tables and their columns are present.

---
**Task 10.2: Create `scripts/run_tournament_game.py`**
* **Description**: Create a script to run a single game between two configurable players (e.g., Stockfish vs. LLM, Stockfish vs. Stockfish).
* **Files to Create/Modify**: `lexichess/scripts/run_tournament_game.py`
* **Details**:
    1.  Argument parsing (e.g., using `argparse`) for:
        * White player type ('stockfish', 'openai_llm', 'ollama_llm') and name.
        * Black player type ('stockfish', 'openai_llm', 'ollama_llm') and name.
        * Stockfish skill/ELO for Stockfish players.
        * LLM model name for LLM players.
        * Time control (e.g., "5+3" -> 300s initial, 5s increment).
        * (Optional) OpenAI API key (better to use environment variables).
    2.  Initialize DB session.
    3.  Initialize `PromptGenerator`.
    4.  Create `Player` instances based on arguments:
        * If 'stockfish', instantiate `StockfishPlayer`.
        * If 'openai_llm', instantiate `OpenAIClient`.
        * If 'ollama_llm', instantiate `OllamaClient`.
    5.  Instantiate `TournamentManager(db_session, prompt_generator)`.
    6.  Call `tournament_manager.play_game(white_player, black_player, time_control_tuple)`.
    7.  Print basic game progress to console (e.g., "Move X: {player} plays {move}").
    8.  Print final game result.
* **Start**: Script does not exist.
* **End**: Script can run a full game, logging all data to the database, and print results.
* **Test**:
    * Run `python scripts/run_tournament_game.py --white-type stockfish --black-type stockfish`. Verify game completes and data is in DB.
    * (If API key and/or Ollama is set up) Run `python scripts/run_tournament_game.py --white-type stockfish --black-type openai_llm --black-model gpt-3.5-turbo`. Verify game completes.
    * Inspect `lexichess.db` after each run to confirm `games`, `moves`, `llm_conversations` (if LLM played), and potentially `hallucinations` are populated correctly.

---
### XI. Documentation & Refinements for MVP
---
**Task 11.1: Basic Unit Tests for Critical Functions**
* **Description**: Write basic passing unit tests for a few critical, non-IO-bound functions.
* **Files to Create/Modify**: Files in `tests/chess/`, `tests/llm/`.
* **Details**:
    * `tests/chess/test_board.py`: Test move validation (`is_move_legal`) for a few more cases. Test game outcome for stalemate.
    * `tests/chess/test_time_control.py`: Test complex time deductions and increment scenarios.
    * `tests/llm/test_prompt.py`: Test `extract_san_from_response` with more edge cases.
* **Start**: Some tests exist, but coverage can be improved for core logic.
* **End**: A few more robust unit tests for pure functions are added and pass.
* **Test**: Run `pytest tests/`. All new and existing tests should pass.

---
**Task 11.2: Update `README.md` - Getting Started for MVP**
* **Description**: Update the `README.md` with instructions on how to set up the environment, database, and run the MVP tournament script.
* **Files to Create/Modify**: `lexichess/README.md`
* **Details**:
    * Python version.
    * How to install dependencies (e.g., `poetry install`).
    * How to set up Stockfish (if manual path is needed).
    * How to set OpenAI API Key (environment variable `OPENAI_API_KEY`).
    * How to set up and run Ollama for local LLMs.
    * Command to initialize the database: `python scripts/setup_db.py`.
    * Example command to run a game: `python scripts/run_tournament_game.py ...`.
* **Start**: README "Getting Started" section is likely a TODO.
* **End**: README contains clear, actionable instructions for setting up and running the MVP.
* **Test**: Another developer (or you, in a fresh environment) should be able to follow the README instructions to run a game successfully.

---
This concludes the granular plan for the LexiChess MVP. Each task is designed to be a small, manageable, and testable piece of work.