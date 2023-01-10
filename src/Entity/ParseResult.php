<?php

namespace App\Entity;

class ParseResult implements \ArrayAccess, \Countable
{
    private array $extra;

    public function __construct(array $data, array $extra = [])
    {
        $this->data = $data;
        $this->extra = $extra;
    }

    public function getExtras(object $object): array
    {
        return $this->extra[spl_object_hash($object)] ?? [];
    }

    public function getExtra(object $object, string $name): mixed
    {
        return $this->extra[spl_object_hash($object)][$name] ?? null;
    }

    public function offsetExists(mixed $offset): bool
    {
        return array_key_exists($offset, $this->data);
    }

    public function offsetGet(mixed $offset): mixed
    {
        return $this->data[$offset];
    }

    public function offsetSet(mixed $offset, mixed $value): void
    {
        $this->data[$offset] = $value;
    }

    public function offsetUnset(mixed $offset): void
    {
        unset($this->data[$offset]);
    }

    public function count(): int
    {
        return count($this->data);
    }
}
