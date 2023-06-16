<?php

namespace App\Helper;

use App\Entity\Member;
use Symfony\Component\Console\Helper\TableCellStyle;

class MemberMatch
{
    public const SCORE_HIGH = 1000;
    public const SCORE_MEDIUM = 100;
    public const SCORE_LOW = 10;
    public const SCORE_ZERO = 0;

    private ?string $hint = null;

    public static function high(Member $memberSource, ?Member $result): self
    {
        return new self($memberSource, $result, self::SCORE_HIGH);
    }

    public static function medium(Member $memberSource, ?Member $result): self
    {
        return new self($memberSource, $result, self::SCORE_MEDIUM);
    }

    public static function low(Member $memberSource, ?Member $result): self
    {
        return new self($memberSource, $result, self::SCORE_LOW);
    }

    public static function zero(Member $memberSource): self
    {
        return new self($memberSource, null, self::SCORE_ZERO);
    }

    public function __construct(protected Member $memberSource, protected ?Member $result, protected int $score)
    {
    }

    public function scoreToString(): string
    {
        $result = match ($this->score) {
            self::SCORE_HIGH => 'high',
            self::SCORE_MEDIUM => 'medium',
            self::SCORE_LOW => 'low',
            self::SCORE_ZERO => 'none',
            default => sprintf('(%d)', $this->score)
        };

        return $this->hint ? sprintf('%s(%s)', $result, $this->hint) : $result;
    }

    public function scoreTableCellStyle(): TableCellStyle
    {
        // (black, red, green, yellow, blue, magenta, cyan, white,
        // default, gray, bright-red, bright-green, bright-yellow, bright-blue, bright-magenta, bright-cyan, etc
        $tag = match ($this->score) {
            self::SCORE_HIGH => '<fg=green>',
            self::SCORE_MEDIUM => '<fg=yellow>',
            self::SCORE_LOW => '<fg=red>',
            self::SCORE_ZERO => '<fg=gray>',
            default => '<fg=default>',
        };

        return new TableCellStyle(['cellFormat' => $tag.'%s</>']);
    }

    public function __toString(): string
    {
        return $this->scoreToString();
    }

    public function getMember(): Member
    {
        return $this->memberSource;
    }

    public function getResult(): ?Member
    {
        return $this->result;
    }

    public function getHint(): ?string
    {
        return $this->hint;
    }

    public function setHint(?string $hint): self
    {
        $this->hint = $hint;

        return $this;
    }

    public function getScore(): int
    {
        return $this->score;
    }
}
