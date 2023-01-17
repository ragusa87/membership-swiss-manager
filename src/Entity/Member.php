<?php

namespace App\Entity;

use App\Repository\MemberRepository;
use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\DBAL\Types\Types;
use Doctrine\ORM\Mapping as ORM;
use Gedmo\Timestampable\Traits\TimestampableEntity;

#[ORM\Entity(repositoryClass: MemberRepository::class)]
class Member
{
    use TimestampableEntity;

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

    #[ORM\ManyToOne(targetEntity: self::class, inversedBy: 'children')]
    #[ORM\JoinColumn(name: 'parent_id', referencedColumnName: 'id')]
    private ?self $parent = null;

    #[ORM\OneToMany(mappedBy: 'member', targetEntity: MemberSubscription::class, orphanRemoval: true, cascade: ['persist', 'remove'])]
    private Collection $memberSubscription;

    #[ORM\Column(length: 255, nullable: true)]
    private ?string $address = null;

    #[ORM\Column(length: 20, nullable: true)]
    private ?string $addressNumber = null;

    #[ORM\Column(length: 255, nullable: true)]
    private ?string $city = null;

    #[ORM\Column(length: 255, nullable: true)]
    private ?string $phone = null;

    #[ORM\Column(nullable: true)]
    private ?int $zip = null;

    /**
     * @var Collection|Member[]
     */
    #[ORM\OneToMany(mappedBy: 'parent', targetEntity: self::class)]
    protected Collection $children;

    public function __construct()
    {
        $this->children = new ArrayCollection();
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

    public function setFirstname(?string $firstname = null): self
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
     * @return Collection<int, MemberSubscription>
     */
    public function getMemberSubscription(): Collection
    {
        return $this->memberSubscription;
    }

    public function addMemberSubscription(MemberSubscription $memberSubscription): self
    {
        if (!$this->memberSubscription->contains($memberSubscription)) {
            $this->memberSubscription->add($memberSubscription);
            $memberSubscription->setMember($this);
        }

        return $this;
    }

    public function removeMemberSubscription(MemberSubscription $memberSubscription): self
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

    public function getAddress(): ?string
    {
        return $this->address;
    }

    public function setAddress(?string $address): self
    {
        $this->address = $address;

        return $this;
    }

    public function getCity(): ?string
    {
        return $this->city;
    }

    public function setCity(?string $city): self
    {
        $this->city = $city;

        return $this;
    }

    public function getPhone(): ?string
    {
        return $this->phone;
    }

    public function setPhone(?string $phone): self
    {
        $this->phone = $phone;

        return $this;
    }

    public function getZip(): ?int
    {
        return $this->zip;
    }

    public function setZip(?int $zip): self
    {
        $this->zip = $zip;

        return $this;
    }

    public function setCityAndZip(?string $npaAndCity): self
    {
        if (null === $npaAndCity) {
            return $this;
        }
        $explode = explode(' ', $npaAndCity);
        foreach ($explode as $index => $element) {
            if (1 === preg_match('/[0-9]+/', $element)) {
                $this->setZip((int) $element);
                unset($explode[$index]);
                break;
            }
        }
        $city = implode(' ', $explode);
        $this->setCity('' === trim((string) $city) ? null : trim($city));

        return $this;
    }

    /**
     * @return Collection|Member[]
     */
    public function getChildren(): Collection
    {
        return $this->children;
    }

    public function merge(Member $copy): self
    {
        // TODO move into a service and use more intelligent merge (DeepClone or annotation reader)
        $this->setLastname($copy->getLastname());
        $this->setFirstname($copy->getFirstname());
        $this->setEmail($copy->getEmail());
        $this->setAddress($copy->getAddress());
        $this->setAddressNumber($copy->getAddressNumber());
        $this->setCity($copy->getCity());
        $this->setZip($copy->getZip());
        $this->setPhone($copy->getPhone());
        $this->setComment($copy->getComment());
        $this->setParent($copy->getParent());

        return $this;
    }

    public function getMemberSubscriptionBySubscription(Subscription $subscription): ?MemberSubscription
    {
        /** @var MemberSubscription $memberSubscription */
        foreach ($this->memberSubscription as $memberSubscription) {
            if ($memberSubscription->getSubscription() === $subscription) {
                return $memberSubscription;
            }
        }

        return null;
    }

    public function getFullname(): string
    {
        return implode(' ', [$this->firstname, $this->lastname]);
    }

    public function getCountry(): string
    {
        return 'CH';
    }

    public function getAddressNumber(): ?string
    {
        return $this->addressNumber;
    }

    public function setAddressNumber(?string $addressNumber): self
    {
        $this->addressNumber = $addressNumber;

        return $this;
    }

    public function getFullAddressLine1(): ?string
    {
        if (null == $this->getAddress() && null == $this->getAddressNumber()) {
            return null;
        }

        return trim(sprintf('%s %s', $this->getAddress() ?? '', $this->getAddressNumber()));
    }

    public function getFullAddressLine2(): ?string
    {
        if (null == $this->getCity() && null == $this->getZip()) {
            return null;
        }

        return trim(sprintf('%s %s', $this->getCity() ?? '', $this->getZip()));
    }
}
