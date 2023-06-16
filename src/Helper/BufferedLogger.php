<?php

namespace App\Helper;

use Psr\Log\LoggerAwareInterface;
use Psr\Log\LoggerAwareTrait;
use Psr\Log\LoggerInterface;
use Psr\Log\LoggerTrait;
use Psr\Log\NullLogger;

class BufferedLogger implements LoggerInterface, LoggerAwareInterface
{
    use LoggerAwareTrait;
    use LoggerTrait;

    protected array $buffer = [];

    public function log($level, \Stringable|string $message, array $context = []): void
    {
        $this->buffer[] = [
            'level' => $level,
            'message' => $message,
            'context' => $context,
        ];
        $this->logger()->log($level, $message, $context);
    }

    public function getLogs(): array
    {
        $buffer = $this->buffer;
        $this->buffer = [];

        return $buffer;
    }

    private function logger(): LoggerInterface
    {
        return $this->logger ??= new NullLogger();
    }
}
