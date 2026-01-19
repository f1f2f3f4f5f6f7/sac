// ... existing imports ...

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [
    RouterModule, 
    CommonModule, 
    StyleClassModule, 
    AppConfigurator,
    Drawer,
    ButtonModule
    // Quita los demás imports que ya no necesitas si el drawer está vacío
  ],
  template: ` 
    <div class="layout-topbar">
      <!-- ... existing topbar code ... -->
      
      <div class="layout-topbar-actions">
        <div class="layout-config-menu">
          <button type="button" class="layout-topbar-action" (click)="toggleDarkMode()">
            <i
              [ngClass]="{
                'pi ': true,
                'pi-moon': layoutService.isDarkTheme(),
                'pi-sun': !layoutService.isDarkTheme()
              }"
            ></i>
          </button>
          <app-configurator />
        </div>

        <button
          class="layout-topbar-menu-button layout-topbar-action"
          pStyleClass="@next"
          enterFromClass="hidden"
          enterActiveClass="animate-scalein"
          leaveToClass="hidden"
          leaveActiveClass="animate-fadeout"
          [hideOnOutsideClick]="true"
        >
          <i class="pi pi-ellipsis-v"></i>
        </button>

        <div class="layout-topbar-menu hidden lg:block">
          <div class="layout-topbar-menu-content">
            <button type="button" class="layout-topbar-action" (click)="openProfileDrawer()">
              <i class="pi pi-user"></i>
              <span>Perfil</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- DRAWER VACÍO -->
    <p-drawer 
      [(visible)]="profileDrawerVisible" 
      position="right" 
      [modal]="true"
      [style]="{ width: '20rem' }"
      styleClass="w-20rem">
    </p-drawer>
  `,
  providers: [MessageService]
})
export class AppTopbar implements OnInit, OnDestroy {
  items!: MenuItem[];
  profileDrawerVisible = false;
  
  // Puedes eliminar todas las propiedades relacionadas con profile, password, preferences, etc.
  // si ya no las necesitas

  private destroy$ = new Subject<void>();

  constructor(
    public layoutService: LayoutService,
    private router: Router,
    private authService: AuthService
    // Puedes quitar UsersService y MessageService si ya no los usas
  ) {}

  ngOnInit() {
    // Puedes eliminar loadUserProfile() y loadPreferences() si ya no los necesitas
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  toggleDarkMode() {
    this.layoutService.layoutConfig.update((state) => ({ ...state, darkTheme: !state.darkTheme }));
  }

  openProfileDrawer() {
    this.profileDrawerVisible = true;
  }

  // Puedes eliminar saveProfile() y updatePassword() si ya no los necesitas
}