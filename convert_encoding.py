import codecs

source_filename = "pytest.ini"
target_filename = "pytest.ini"
source_encoding = "utf-8"  # 尝试使用 gbk 编码读取，如果不行可以尝试其他编码
target_encoding = "utf-8"

try:
    with codecs.open(source_filename, mode="r", encoding=source_encoding) as source_file:
        content = source_file.read()

    with codecs.open(target_filename, mode="w", encoding=target_encoding) as target_file:
        target_file.write(content)

    print(f"Successfully converted {source_filename} from {source_encoding} to {target_encoding}")

except Exception as e:
    print(f"Error converting {source_filename}: {e}")
