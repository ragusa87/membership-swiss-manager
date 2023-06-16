<?php

namespace App\Twig;

use Twig\Extension\AbstractExtension;
use Twig\TwigFunction;

class TwigEnvironmentInjector extends AbstractExtension
{
    private string $databaseDsn;

    public function __construct(string $databaseDsn)
    {
        $this->databaseDsn = $databaseDsn;
    }

    public function getEnvironment(): string
    {
        if (str_contains($this->databaseDsn, 'prod')) {
            return 'prod';
        }

        return 'dev';
    }

        public function getFunctions(): array
        {
            return [
                new TwigFunction('getEnvironment', [$this, 'getEnvironment']),
            ];
        }
}
