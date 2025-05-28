# def run_paralelly

Paralelly runs provided functions with or without args.

### With args:
```python
if __name__ == "__main__":
    run_paralelly(
        [f1, f2, f3, f4],
        [
            (1, 2),
            (3, 4),
            (5, 6),
            (7, 8)
        ]
    )
```

### Without args:
```python
if __name__ == "__main__":
    run_paralelly([f1, f2, f3, f4])
```

## Make sure you call function from `if __name__ == "__main__"`, otherwise it will FAIL!