DELETE FROM {vector_name}
    WHERE metadata->>'source' = '{source_delete}'