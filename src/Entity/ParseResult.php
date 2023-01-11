<?php

namespace App\Entity;

/*
 * @template T
 */
class ParseResult extends \ArrayIterator
{
    private array $extra;

    public function __construct(array $data, array $extra = [])
    {
        parent::__construct($data);
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
}
