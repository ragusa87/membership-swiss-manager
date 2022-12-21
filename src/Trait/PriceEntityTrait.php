<?php

namespace App\Trait;

use Doctrine\ORM\Mapping as ORM;

trait PriceEntityTrait
{
    #[ORM\Column(nullable: true)]
    private ?int $price = 0;

    public function setPrice(?int $price): self
    {
        $this->price = $price;

        return $this;
    }

    public function getPrice(): ?int
    {
        return $this->price;
    }

    public function getFormattedPrice(): ?string
    {
        $priceInt = $this->getPrice();
        if (null === $priceInt) {
            return null;
        }

        return number_format($this->price / 10.0, 2);
    }
}
