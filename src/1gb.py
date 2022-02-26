with open("server/data/1gb", "wb") as out:
    out.seek((1024 * 1024 * 100) - 1)
    out.write(b'\0')