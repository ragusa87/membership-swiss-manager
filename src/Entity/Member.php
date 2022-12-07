<?php

namespace App\Entity;

use App\Repository\MemberRepository;
use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\DBAL\Types\Types;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: MemberRepository::class)]
class Member
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(length: 255)]
    private ?string $firstname = null;

    #[ORM\Column(length: 255, nullable: true)]
    private ?string $lastname = null;

    #[ORM\Column(length: 255, nullable: true)]
    private ?string $email = null;

    #[ORM\Column(type: Types::TEXT, nullable: true)]
    private ?string $comment = null;

    #[ORM\OneToOne(targetEntity: self::class)]
    #[ORM\JoinColumn(name: 'parent_id', referencedColumnName: 'id')]
    private ?self $parent = null;

    #[ORM\OneToMany(mappedBy: 'member', targetEntity: MemberSubscription::class, orphanRemoval: true, cascade: ['persist', 'remove'])]
    private Collection $memberSubscription;

    public function __construct()
    {
        $this->memberSubscription = new ArrayCollection();
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function getFirstname(): ?string
    {
        return $this->firstname;
    }

    public function setFirstname(string $firstname): self
    {
        $this->firstname = $firstname;

        return $this;
    }

    public function getLastname(): ?string
    {
        return $this->lastname;
    }

    public function setLastname(?string $lastname): self
    {
        $this->lastname = $lastname;

        return $this;
    }

    public function getEmail(): ?string
    {
        return $this->email;
    }

    public function setEmail(?string $email): self
    {
        $this->email = $email;

        return $this;
    }

    public function getComment(): ?string
    {
        return $this->comment;
    }

    public function setComment(?string $comment): self
    {
        $this->comment = $comment;

        return $this;
    }

    public function getParent(): ?self
    {
        return $this->parent;
    }

    public function setParent(?self $parent): self
    {
        // // unset the owning side of the relation if necessary
        // if (null === $parent && null !== $this->parent) {
        //     $this->parent->setParent(null);
        // }

        // // set the owning side of the relation if necessary
        // if (null !== $parent && $parent->getParent() !== $this) {
        //     $parent->setParent($this);
        // }

        $this->parent = $parent;

        return $this;
    }

    /**
     * @return Collection<int, membersubscription>
     */
    public function getMemberSubscription(): Collection
    {
        return $this->memberSubscription;
    }

    public function addMemberSubscription(membersubscription $memberSubscription): self
    {
        if (!$this->memberSubscription->contains($memberSubscription)) {
            $this->memberSubscription->add($memberSubscription);
            $memberSubscription->setMember($this);
        }

        return $this;
    }

    public function removeMemberSubscription(membersubscription $memberSubscription): self
    {
        if ($this->memberSubscription->removeElement($memberSubscription)) {
            // set the owning side to null (unless already changed)
            if ($memberSubscription->getMember() === $this) {
                $memberSubscription->setMember(null);
            }
        }

        return $this;
    }

    public function __toString(): string
    {
        $properties = [$this->firstname, null !== $this->lastname ? strtoupper($this->lastname) : $this->lastname];
        $properties = array_filter($properties);

        return implode(' ', $properties);
    }
}
