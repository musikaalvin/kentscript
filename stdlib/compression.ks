:: compression - File compression and decompression
:: Support for gzip, zlib, bz2, lzma

:: ─── Gzip ───────────────────────────────────────────────────────────────────

func gzip_compress(data, level) {
    if level == none { level = 6; }
    return gzip_compress_impl(data, level);
}

func gzip_decompress(data) {
    return gzip_decompress_impl(data);
}

class GzipFile {
    func __init__(self, filename, mode, level) {
        self.filename = filename;
        self.mode = mode != none ? mode : "rb";
        self.level = level != none ? level : 6;
        self.file = none;
        self.buffer = [];
    }
    
    func open(self) {
        self.file = file_open(self.filename, self.mode);
    }
    
    func read(self, size) {
        if self.file == none {
            self.open();
        }
        
        let compressed = file_read(self.file, size);
        return gzip_decompress(compressed);
    }
    
    func write(self, data) {
        if self.file == none {
            self.open();
        }
        
        let compressed = gzip_compress(data, self.level);
        file_write(self.file, compressed);
    }
    
    func close(self) {
        if self.file != none {
            file_close(self.file);
            self.file = none;
        }
    }
}

:: ─── Zlib ───────────────────────────────────────────────────────────────────

func zlib_compress(data, level) {
    if level == none { level = 6; }
    return zlib_compress_impl(data, level);
}

func zlib_decompress(data) {
    return zlib_decompress_impl(data);
}

func zlib_adler32(data, value) {
    if value == none { value = 1; }
    return zlib_adler32_impl(data, value);
}

func zlib_crc32(data, value) {
    if value == none { value = 0; }
    return zlib_crc32_impl(data, value);
}

:: ─── Bzip2 ──────────────────────────────────────────────────────────────────

func bz2_compress(data, level) {
    if level == none { level = 9; }
    return bz2_compress_impl(data, level);
}

func bz2_decompress(data) {
    return bz2_decompress_impl(data);
}

class BZ2File {
    func __init__(self, filename, mode, level) {
        self.filename = filename;
        self.mode = mode != none ? mode : "rb";
        self.level = level != none ? level : 9;
        self.file = none;
    }
    
    func open(self) {
        self.file = file_open(self.filename, self.mode);
    }
    
    func read(self, size) {
        if self.file == none {
            self.open();
        }
        
        let compressed = file_read(self.file, size);
        return bz2_decompress(compressed);
    }
    
    func write(self, data) {
        if self.file == none {
            self.open();
        }
        
        let compressed = bz2_compress(data, self.level);
        file_write(self.file, compressed);
    }
    
    func close(self) {
        if self.file != none {
            file_close(self.file);
            self.file = none;
        }
    }
}

:: ─── LZMA ───────────────────────────────────────────────────────────────────

func lzma_compress(data, format, check, preset) {
    if format == none { format = "xz"; }
    if check == none { check = "crc64"; }
    if preset == none { preset = 6; }
    return lzma_compress_impl(data, format, check, preset);
}

func lzma_decompress(data, format) {
    if format == none { format = "auto"; }
    return lzma_decompress_impl(data, format);
}

class LZMAFile {
    func __init__(self, filename, mode, format, check, preset) {
        self.filename = filename;
        self.mode = mode != none ? mode : "rb";
        self.format = format != none ? format : "xz";
        self.check = check != none ? check : "crc64";
        self.preset = preset != none ? preset : 6;
        self.file = none;
    }
    
    func open(self) {
        self.file = file_open(self.filename, self.mode);
    }
    
    func read(self, size) {
        if self.file == none {
            self.open();
        }
        
        let compressed = file_read(self.file, size);
        return lzma_decompress(compressed, self.format);
    }
    
    func write(self, data) {
        if self.file == none {
            self.open();
        }
        
        let compressed = lzma_compress(data, self.format, self.check, self.preset);
        file_write(self.file, compressed);
    }
    
    func close(self) {
        if self.file != none {
            file_close(self.file);
            self.file = none;
        }
    }
}

:: ─── Tar ────────────────────────────────────────────────────────────────────

class TarFile {
    func __init__(self, name, mode) {
        self.name = name;
        self.mode = mode != none ? mode : "r";
        self.members = [];
    }
    
    func add(self, name, arcname) {
        if arcname == none { arcname = name; }
        let data = file_read_all(name);
        self.members.push({"name": arcname, "data": data});
    }
    
    func extract(self, path) {
        for member in self.members {
            let filepath = path + "/" + member.name;
            file_write_all(filepath, member.data);
        }
    }
    
    func extractall(self, path) {
        self.extract(path);
    }
    
    func getmembers(self) {
        return self.members;
    }
    
    func getnames(self) {
        return self.members.map((m) => m.name);
    }
    
    func close(self) {
        self.members = [];
    }
}

func tar_open(name, mode) {
    return TarFile(name, mode);
}

:: ─── Zip ────────────────────────────────────────────────────────────────────

class ZipFile {
    func __init__(self, file, mode, compression) {
        self.file = file;
        self.mode = mode != none ? mode : "r";
        self.compression = compression != none ? compression : "deflate";
        self.members = [];
    }
    
    func write(self, filename, arcname) {
        if arcname == none { arcname = filename; }
        let data = file_read_all(filename);
        let compressed = zlib_compress(data);
        self.members.push({"name": arcname, "data": compressed});
    }
    
    func read(self, name) {
        for member in self.members {
            if member.name == name {
                return zlib_decompress(member.data);
            }
        }
        raise f"File not found: {name}";
    }
    
    func extract(self, member, path) {
        let data = self.read(member);
        let filepath = path + "/" + member;
        file_write_all(filepath, data);
    }
    
    func extractall(self, path) {
        for member in self.members {
            self.extract(member.name, path);
        }
    }
    
    func namelist(self) {
        return self.members.map((m) => m.name);
    }
    
    func close(self) {
        self.members = [];
    }
}

:: Runtime interface
func gzip_compress_impl(data, level) { return system_gzip_compress(data, level); }
func gzip_decompress_impl(data) { return system_gzip_decompress(data); }
func zlib_compress_impl(data, level) { return system_zlib_compress(data, level); }
func zlib_decompress_impl(data) { return system_zlib_decompress(data); }
func zlib_adler32_impl(data, value) { return system_zlib_adler32(data, value); }
func zlib_crc32_impl(data, value) { return system_zlib_crc32(data, value); }
func bz2_compress_impl(data, level) { return system_bz2_compress(data, level); }
func bz2_decompress_impl(data) { return system_bz2_decompress(data); }
func lzma_compress_impl(data, format, check, preset) { return system_lzma_compress(data, format, check, preset); }
func lzma_decompress_impl(data, format) { return system_lzma_decompress(data, format); }
func file_open(filename, mode) { return system_file_open(filename, mode); }
func file_read(file, size) { return system_file_read(file, size); }
func file_write(file, data) { system_file_write(file, data); }
func file_close(file) { system_file_close(file); }
func file_read_all(filename) { return system_file_read_all(filename); }
func file_write_all(filename, data) { system_file_write_all(filename, data); }

export {
    gzip_compress, gzip_decompress, GzipFile,
    zlib_compress, zlib_decompress, zlib_adler32, zlib_crc32,
    bz2_compress, bz2_decompress, BZ2File,
    lzma_compress, lzma_decompress, LZMAFile,
    TarFile, tar_open,
    ZipFile
};

:: Archive listing and member access
func zip_list(path) {
    return system_archive_list_zip(path);
}

func zip_read(path, member) {
    return system_archive_read_zip(path, member);
}

func tar_list(path) {
    return system_archive_list_tar(path);
}

func tar_read(path, member) {
    return system_archive_read_tar(path, member);
}

func zip_create(path, files) {
    return system_archive_create_zip(path, files);
}

func zip_extract(path, dest) {
    if dest == none { dest = "."; }
    return system_archive_extract_zip(path, dest);
}

func tar_create(path, files) {
    return system_archive_create_tar(path, files);
}

func tar_extract(path, dest) {
    if dest == none { dest = "."; }
    return system_archive_extract_tar(path, dest);
}
