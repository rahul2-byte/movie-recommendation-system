import sys
import pandas as pd
import struct
import os

# Define the input path - relative to project root usually
DEFAULT_INPUT_FILE = "backend/data/processed/ratings.parquet"

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT_FILE
    
    if not os.path.exists(input_file):
        sys.stderr.write(f"Error: Input file {input_file} not found. CWD: {os.getcwd()}\n")
        sys.exit(1)

    try:
        # Load Parquet
        # We only need specific columns
        df = pd.read_parquet(input_file, columns=["userId", "movieId", "rating", "timestamp"])
        
        sys.stderr.write(f"Python: Loaded {len(df)} rows. Streaming to C++...\n")

        # Ensure correct types for binary packing
        # int32, int32, float, int64 matches C++ struct
        # 'iiqd' = int, int, long long (q=8 bytes), double (d=8 bytes)? 
        # Wait, C++ struct:
        # int32_t userId; (4)
        # int32_t movieId; (4)
        # float rating;   (4)
        # int64_t timestamp; (8)
        # Total packed size = 4+4+4+8 = 20 bytes? 
        # struct padding might align it to 24.
        # Let's use standard packing '=' to avoid padding issues or handle alignment.
        # C++ struct alignment usually aligns 8-byte types to 8-byte boundaries.
        # 4 (int) + 4 (int) + 4 (float) + 4 (padding) + 8 (int64) = 24 bytes likely.
        
        # To be safe, we will use __attribute__((packed)) in C++ OR just simple packing here and handle it.
        # Ideally, '2i f q' is:
        # i = 4
        # f = 4
        # q = 8
        # = 16 bytes.
        
        # Let's adjust C++ struct to be safe. I'll modify C++ to #pragma pack(1) or similar.
        # actually, let's just use Python struct '2i f q' (standard size) and tell C++ to read tightly.
        
        # For this script, I will use `itertuples` which is faster than iterrows
        # But writing in bulk is faster.
        # DataFrame to records?
        
        # Fastest way: use numpy tobytes()
        # Create a structured array
        import numpy as np
        
        # Structured array matching C++ struct
        # int32, int32, float32, int64
        dtype = np.dtype([
            ('userId', 'i4'),
            ('movieId', 'i4'),
            ('rating', 'f4'),
            ('timestamp', 'i8')
        ])
        
        # Convert df to numpy
        # Ensure column order matches!
        arr = np.zeros(len(df), dtype=dtype)
        arr['userId'] = df['userId'].to_numpy(dtype='int32')
        arr['movieId'] = df['movieId'].to_numpy(dtype='int32')
        arr['rating'] = df['rating'].to_numpy(dtype='float32')
        arr['timestamp'] = df['timestamp'].to_numpy(dtype='int64')
        
        # Write bytes directly to stdout buffer
        sys.stdout.buffer.write(arr.tobytes())
        
        sys.stderr.write("Python: Streaming complete.\n")

    except Exception as e:
        sys.stderr.write(f"Error in bridge: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
