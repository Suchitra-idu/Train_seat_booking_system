<script>
  // The one place lucide is imported (D27): a name -> component lookup so callers write
  // <Icon name="train" /> instead of importing a different lucide component per file.
  import {
    TrainFront,
    Search,
    Check,
    CircleCheck,
    Lock,
    TriangleAlert,
    Clock,
    Ticket,
    Armchair,
    QrCode,
    Printer,
    Download,
    MapPin,
    Calendar,
    Users,
    User,
    ChevronLeft,
    ChevronRight,
    ArrowRight,
    ArrowLeft,
    X,
  } from "lucide-svelte";

  const ICONS = {
    train: TrainFront,
    search: Search,
    check: Check,
    "circle-check": CircleCheck,
    lock: Lock,
    alert: TriangleAlert,
    clock: Clock,
    ticket: Ticket,
    seat: Armchair,
    qr: QrCode,
    printer: Printer,
    download: Download,
    "map-pin": MapPin,
    calendar: Calendar,
    users: Users,
    user: User,
    "chevron-left": ChevronLeft,
    "chevron-right": ChevronRight,
    "arrow-right": ArrowRight,
    "arrow-left": ArrowLeft,
    close: X,
  };

  let { name, class: cls = "size-4" } = $props();
  const Cmp = $derived(ICONS[name] ?? TrainFront);
</script>

<Cmp class={cls} />
