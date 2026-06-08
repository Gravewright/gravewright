## Summary

Describe what this pull request changes.

## Type of change

- [ ] Bug fix
- [ ] Feature
- [ ] Documentation
- [ ] Refactor
- [ ] Performance
- [ ] Security hardening
- [ ] Tests
- [ ] Maintenance / chore

## Alpha risk

Does this change affect existing tables, schemas, saves, storage layout, public APIs, systems, modules, or upgrade behavior?

- [ ] No alpha-risk impact expected
- [ ] May affect existing Alpha data
- [ ] Breaking change
- [ ] Schema/storage change
- [ ] Public API change

## Checklist

- [ ] I kept the change focused.
- [ ] I updated or added tests where appropriate.
- [ ] I updated documentation where appropriate.
- [ ] I did not commit local runtime data, databases, logs, secrets, or generated performance outputs.
- [ ] I did not commit `.env`, `.env.local`, `.env.*.local`, or private environment files.
- [ ] I considered whether this change affects systems or modules.

## Testing

Describe what you ran:

```bash
uv run pytest tests/unit
uv run python -m compileall app tests scripts main.py
```

## Notes for reviewers

Add anything reviewers should pay attention to.
