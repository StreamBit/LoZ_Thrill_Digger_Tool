#pragma once

extern "C" {

// Initialize a new board:
//   rows, cols = grid dimensions
//   bombs = total bombs on the board
//   sample_count = number of Monte Carlo trials
__declspec(dllexport)
void ms_init(int rows, int cols, int bombs, int sample_count);

// Change the Monte Carlo sample count (without re‑initializing the board):
__declspec(dllexport)
void ms_set_sample_count(int sample_count);

// Mark or clear a revealed cell:
//   r, c = zero‑based row/column
//   value =
//     -1 → unknown
//      0 → Green hint (0 adjacent bombs)
//      1 → Blue  hint (1–2 adjacent bombs)
//      2 → Red   hint (3–4 adjacent bombs)
//      3 → Silver hint (5–6 adjacent bombs)
//      4 → Gold  hint (7–8 adjacent bombs)
//      5 → Revealed bomb
__declspec(dllexport)
void ms_set_cell(int r, int c, int value);

// Run the Monte Carlo solver.  out_probs must point to a float array of length rows*cols.
__declspec(dllexport)
void ms_solve(float* out_probs);

// Run **exact** enumeration over all valid bomb‑placements.
// For small boards this will compute 100% accurate probabilities.
// out_probs same format as above.
__declspec(dllexport)
void ms_solve_exact(float* out_probs);

// Free any internal state.
__declspec(dllexport)
void ms_cleanup();

} // extern "C"
