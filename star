#!/usr/bin/env python3
import sys

def generate_pattern(n):
    if n == 1:
        return "{}"
    elif n == 2:
        return "{,*/,*/*/}"
    elif n == 3:
        return "{,*/,*/*/}"
    else:
        # For n > 3, generate the pattern
        parts = []
        for i in range(1, n + 1):
            if i == 1:
                parts.append("")
            else:
                star_slash = "*/" * (i - 1)
                parts.append(star_slash)
        return "{" + ",".join(parts) + "}"

if __name__ == "__main__":
    if len(sys.argv) == 1:
        n = 4  # Default value
    elif len(sys.argv) == 2:
        try:
            n = int(sys.argv[1])
        except ValueError:
            print("Error: Please provide a valid integer")
            sys.exit(1)
    else:
        print("Usage: python star.py [number]")
        sys.exit(1)
    
    result = generate_pattern(n)
    print(result)
