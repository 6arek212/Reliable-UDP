with open("server/data/1gb-file", "wb") as out:
    out.seek((1024 * 1024 * 1024) - 1)
    out.write(b'\0')