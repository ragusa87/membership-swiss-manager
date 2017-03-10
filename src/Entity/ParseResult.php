<?php

namespace App\Entity;

/**
 * @psalm-template TKey of array-key
 * @psalm-template T
 *
 * @template-extends \ArrayIterator<TKey, T>
 */
class ParseResult extends \ArrayIterator
{
    /**
     * @param array<T>                          $data
     * @param array<string,array<string,mixed>> $extra
     */
    public function __construct(array $data, private array $extra = [])
    {
        parent::__construct($data);
    }

    /**
     * @return array<string,mixed>
     */
    public function getExtras(object $object): array
    {
        return $this->extra[spl_object_hash($object)] ?? [];
    }

    public function getExtra(object $object, string $name): mixed
    {
        return $this->extra[spl_object_hash($object)][$name] ?? null;
    }
}
