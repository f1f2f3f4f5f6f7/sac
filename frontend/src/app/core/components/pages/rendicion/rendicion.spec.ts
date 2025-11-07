import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Rendicion } from './rendicion';

describe('Rendicion', () => {
  let component: Rendicion;
  let fixture: ComponentFixture<Rendicion>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Rendicion]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Rendicion);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
