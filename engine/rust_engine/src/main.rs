use anyhow::{Context, Result, anyhow, bail};
use chess::{Board, BoardStatus, ChessMove, Color, File, MoveGen, Piece, Rank, Square};
use clap::{Parser, Subcommand};
use serde::Serialize;
use std::cmp::Reverse;
use std::str::FromStr;

const SEARCH_MATE_SCORE: i32 = 100_000;

#[derive(Parser)]
#[command(name = "lexichess-engine")]
#[command(about = "A CPU-first local engine for LexiChess personalities.")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Health,
    Move {
        #[arg(long)]
        fen: String,
        #[arg(long, default_value = "balanced")]
        profile: String,
        #[arg(long, default_value_t = 3)]
        depth: u8,
    },
}

#[derive(Clone, Copy)]
struct PersonalityProfile {
    name: &'static str,
    description: &'static str,
    material_weight: i32,
    center_weight: i32,
    development_weight: i32,
    king_safety_weight: i32,
    pawn_push_weight: i32,
    capture_bias: i32,
}

#[derive(Serialize)]
struct ProfileInfo {
    name: &'static str,
    description: &'static str,
}

#[derive(Serialize)]
struct HealthResponse {
    status: &'static str,
    version: &'static str,
    profiles: Vec<ProfileInfo>,
}

#[derive(Serialize)]
struct MoveResponse {
    status: &'static str,
    profile: &'static str,
    depth: u8,
    best_move_uci: String,
    score: i32,
    nodes: u64,
}

#[derive(Default)]
struct SearchStats {
    nodes: u64,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Health => print_json(&HealthResponse {
            status: "ok",
            version: env!("CARGO_PKG_VERSION"),
            profiles: profiles()
                .iter()
                .map(|profile| ProfileInfo {
                    name: profile.name,
                    description: profile.description,
                })
                .collect(),
        })?,
        Commands::Move {
            fen,
            profile,
            depth,
        } => {
            let board = Board::from_str(&fen).map_err(|_| anyhow!("invalid FEN"))?;
            let profile = profile_by_name(&profile)
                .with_context(|| format!("unknown profile: {profile}"))?;
            let (best_move, score, stats) = choose_move(board, profile, depth)?;
            print_json(&MoveResponse {
                status: "ok",
                profile: profile.name,
                depth,
                best_move_uci: best_move.to_string(),
                score,
                nodes: stats.nodes,
            })?;
        }
    }

    Ok(())
}

fn print_json<T: Serialize>(value: &T) -> Result<()> {
    println!("{}", serde_json::to_string(value)?);
    Ok(())
}

fn choose_move(
    board: Board,
    profile: PersonalityProfile,
    depth: u8,
) -> Result<(ChessMove, i32, SearchStats)> {
    let legal_moves = ordered_moves(&board, profile);
    if legal_moves.is_empty() {
        bail!("no legal moves available")
    }

    let mut best_move = legal_moves[0];
    let mut best_score = -SEARCH_MATE_SCORE;
    let mut stats = SearchStats::default();
    let search_depth = depth.max(1);

    for current_depth in 1..=search_depth {
        let mut current_best_move = best_move;
        let mut current_best_score = -SEARCH_MATE_SCORE;
        let mut alpha = -SEARCH_MATE_SCORE;
        let beta = SEARCH_MATE_SCORE;

        for chess_move in &legal_moves {
            let next_board = board.make_move_new(*chess_move);
            let score = -search(
                &next_board,
                current_depth.saturating_sub(1),
                -beta,
                -alpha,
                profile,
                &mut stats,
            );
            if score > current_best_score {
                current_best_score = score;
                current_best_move = *chess_move;
            }
            if score > alpha {
                alpha = score;
            }
        }

        best_move = current_best_move;
        best_score = current_best_score;
    }

    Ok((best_move, best_score, stats))
}

fn search(
    board: &Board,
    depth: u8,
    mut alpha: i32,
    beta: i32,
    profile: PersonalityProfile,
    stats: &mut SearchStats,
) -> i32 {
    stats.nodes += 1;

    match board.status() {
        BoardStatus::Checkmate => return -SEARCH_MATE_SCORE + i32::from(depth),
        BoardStatus::Stalemate => return 0,
        BoardStatus::Ongoing => {}
    }

    if depth == 0 {
        return evaluate(board, profile);
    }

    let moves = ordered_moves(board, profile);
    if moves.is_empty() {
        return evaluate(board, profile);
    }

    let mut best = -SEARCH_MATE_SCORE;
    for chess_move in moves {
        let next_board = board.make_move_new(chess_move);
        let score = -search(
            &next_board,
            depth.saturating_sub(1),
            -beta,
            -alpha,
            profile,
            stats,
        );
        if score > best {
            best = score;
        }
        if score > alpha {
            alpha = score;
        }
        if alpha >= beta {
            break;
        }
    }

    best
}

fn ordered_moves(board: &Board, profile: PersonalityProfile) -> Vec<ChessMove> {
    let mut moves: Vec<ChessMove> = MoveGen::new_legal(board).collect();
    moves.sort_by_key(|chess_move| Reverse(move_priority(board, *chess_move, profile)));
    moves
}

fn move_priority(board: &Board, chess_move: ChessMove, profile: PersonalityProfile) -> i32 {
    let mut score = 0;
    let source_piece = board.piece_on(chess_move.get_source());

    if let Some(captured_piece) = board.piece_on(chess_move.get_dest()) {
        score += 500 + piece_value(captured_piece) * profile.capture_bias / 100;
    }

    if chess_move.get_promotion().is_some() {
        score += 800;
    }

    if is_center_square(chess_move.get_dest()) {
        score += 30 * profile.center_weight / 100;
    }

    if is_castle_move(source_piece, chess_move) {
        score += 35 * profile.king_safety_weight / 100;
    }

    if source_piece == Some(Piece::Pawn) {
        score += 12 * profile.pawn_push_weight / 100;
    }

    score
}

fn is_castle_move(piece: Option<Piece>, chess_move: ChessMove) -> bool {
    if piece != Some(Piece::King) {
        return false;
    }

    let src = chess_move.get_source();
    let dest = chess_move.get_dest();
    let file_distance = dest.get_file().to_index() as i32 - src.get_file().to_index() as i32;
    file_distance.abs() > 1
}

fn evaluate(board: &Board, profile: PersonalityProfile) -> i32 {
    let white = evaluate_for_color(board, Color::White, profile);
    let black = evaluate_for_color(board, Color::Black, profile);
    match board.side_to_move() {
        Color::White => white - black,
        Color::Black => black - white,
    }
}

fn evaluate_for_color(board: &Board, color: Color, profile: PersonalityProfile) -> i32 {
    let mut score = 0;
    for piece in [
        Piece::Pawn,
        Piece::Knight,
        Piece::Bishop,
        Piece::Rook,
        Piece::Queen,
        Piece::King,
    ] {
        let count = count_piece(board, color, piece);
        score += count * piece_value(piece) * profile.material_weight / 100;
    }

    score += center_control_score(board, color) * profile.center_weight / 100;
    score += development_score(board, color) * profile.development_weight / 100;
    score += king_safety_score(board, color) * profile.king_safety_weight / 100;
    score += pawn_push_score(board, color) * profile.pawn_push_weight / 100;

    score
}

fn count_piece(board: &Board, color: Color, piece: Piece) -> i32 {
    let mask = board.color_combined(color) & board.pieces(piece);
    mask.popcnt() as i32
}

fn center_control_score(board: &Board, color: Color) -> i32 {
    let center = [Square::D4, Square::E4, Square::D5, Square::E5];
    let extended = [
        Square::C3,
        Square::D3,
        Square::E3,
        Square::F3,
        Square::C4,
        Square::F4,
        Square::C5,
        Square::F5,
        Square::C6,
        Square::D6,
        Square::E6,
        Square::F6,
    ];

    let mut score = 0;
    for square in center {
        if board.color_on(square) == Some(color) {
            score += 24;
        }
    }
    for square in extended {
        if board.color_on(square) == Some(color) {
            score += 8;
        }
    }
    score
}

fn development_score(board: &Board, color: Color) -> i32 {
    let (knight_starts, bishop_starts, back_rank) = match color {
        Color::White => ([Square::B1, Square::G1], [Square::C1, Square::F1], Rank::First),
        Color::Black => ([Square::B8, Square::G8], [Square::C8, Square::F8], Rank::Eighth),
    };

    let mut score = 0;
    for square in knight_starts {
        if board.piece_on(square) != Some(Piece::Knight) || board.color_on(square) != Some(color)
        {
            score += 18;
        }
    }
    for square in bishop_starts {
        if board.piece_on(square) != Some(Piece::Bishop) || board.color_on(square) != Some(color)
        {
            score += 14;
        }
    }

    for square in [
        Square::A1,
        Square::B1,
        Square::C1,
        Square::D1,
        Square::E1,
        Square::F1,
        Square::G1,
        Square::H1,
        Square::A8,
        Square::B8,
        Square::C8,
        Square::D8,
        Square::E8,
        Square::F8,
        Square::G8,
        Square::H8,
    ] {
        if square.get_rank() == back_rank
            && board.color_on(square) == Some(color)
            && board.piece_on(square).is_some()
        {
            score -= 2;
        }
    }

    score
}

fn king_safety_score(board: &Board, color: Color) -> i32 {
    let king_square = find_king(board, color);
    let mut score = 0;
    match (color, king_square) {
        (Color::White, Some(Square::G1 | Square::C1)) => score += 28,
        (Color::Black, Some(Square::G8 | Square::C8)) => score += 28,
        (Color::White, Some(Square::E1)) => score -= 12,
        (Color::Black, Some(Square::E8)) => score -= 12,
        _ => {}
    }
    score
}

fn pawn_push_score(board: &Board, color: Color) -> i32 {
    let mut score = 0;
    let pawns = board.pieces(Piece::Pawn) & board.color_combined(color);
    for square in pawns {
        let rank_index = square.get_rank().to_index() as i32;
        score += match color {
            Color::White => rank_index,
            Color::Black => 7 - rank_index,
        };
    }
    score
}

fn find_king(board: &Board, color: Color) -> Option<Square> {
    let kings = board.pieces(Piece::King) & board.color_combined(color);
    kings.into_iter().next()
}

fn piece_value(piece: Piece) -> i32 {
    match piece {
        Piece::Pawn => 100,
        Piece::Knight => 320,
        Piece::Bishop => 330,
        Piece::Rook => 500,
        Piece::Queen => 900,
        Piece::King => 0,
    }
}

fn is_center_square(square: Square) -> bool {
    matches!(
        (square.get_file(), square.get_rank()),
        (File::C | File::D | File::E | File::F, Rank::Third | Rank::Fourth | Rank::Fifth | Rank::Sixth)
    )
}

fn profile_by_name(name: &str) -> Option<PersonalityProfile> {
    profiles()
        .iter()
        .copied()
        .find(|profile| profile.name == name)
}

fn profiles() -> &'static [PersonalityProfile] {
    &[
        PersonalityProfile {
            name: "balanced",
            description: "Even-tempered style with solid development and material balance.",
            material_weight: 100,
            center_weight: 100,
            development_weight: 100,
            king_safety_weight: 100,
            pawn_push_weight: 100,
            capture_bias: 100,
        },
        PersonalityProfile {
            name: "aggressive",
            description: "Pushes the center, values initiative, and leans toward captures.",
            material_weight: 94,
            center_weight: 125,
            development_weight: 120,
            king_safety_weight: 88,
            pawn_push_weight: 122,
            capture_bias: 135,
        },
        PersonalityProfile {
            name: "cautious",
            description: "Values material and king safety over tactical chaos.",
            material_weight: 112,
            center_weight: 92,
            development_weight: 96,
            king_safety_weight: 122,
            pawn_push_weight: 92,
            capture_bias: 96,
        },
        PersonalityProfile {
            name: "trickster",
            description: "Creates messy positions and prioritizes active play.",
            material_weight: 90,
            center_weight: 118,
            development_weight: 128,
            king_safety_weight: 84,
            pawn_push_weight: 128,
            capture_bias: 142,
        },
        PersonalityProfile {
            name: "endgame",
            description: "Simplifies patiently and values long conversion chances.",
            material_weight: 108,
            center_weight: 88,
            development_weight: 92,
            king_safety_weight: 104,
            pawn_push_weight: 100,
            capture_bias: 102,
        },
    ]
}
