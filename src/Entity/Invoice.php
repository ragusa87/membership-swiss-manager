<?php

namespace App\Entity;

use App\Repository\InvoiceRepository;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: InvoiceRepository::class)]
class Invoice
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column]
    private ?int $number = null;

    #[ORM\ManyToOne(inversedBy: 'invoice')]
    #[ORM\JoinColumn(nullable: false)]
    private ?MemberSubscription $memberSubscription = null;

    #[ORM\Column(length: 10, nullable: false, options: ['default' => 'created']) ]
    private string $status;

    public function __construct()
    {
        $this->status = InvoiceStatusEnum::CREATED->value;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function getNumber(): ?int
    {
        return $this->number;
    }

    public function setNumber(int $number): self
    {
        $this->number = $number;

        return $this;
    }

    public function getMemberSubscription(): ?MemberSubscription
    {
        return $this->memberSubscription;
    }

    public function setMemberSubscription(?MemberSubscription $memberSubscription): self
    {
        $this->memberSubscription = $memberSubscription;

        return $this;
    }

    public function setStatusFromEnum(InvoiceStatusEnum $enum): static
    {
        $this->status = $enum->value;

        return $this;
    }

    public function getStatusAsEnum(): InvoiceStatusEnum
    {
        return InvoiceStatusEnum::from($this->status);
    }

    public function getStatus(): ?string
    {
        return $this->status;
    }

    public function setStatus(?string $status): static
    {
        $this->status = $status;

        return $this;
    }
}
