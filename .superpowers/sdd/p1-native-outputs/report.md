# P1 native build outputs

Removed tracked architecture-specific ELF binaries from the native feature,
retrieval, ranking, and training output directories. The C++ sources, Makefiles,
and native orchestration remain available for an explicitly rebuilt experiment;
the canonical Python pipeline does not consume these outputs.

Verification: native source/Makefile presence test, full unit suite, Ruff, and
diff checks.
